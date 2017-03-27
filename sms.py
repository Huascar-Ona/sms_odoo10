# -*- coding: utf-8 -*-
from odoo import api,fields,models
import jsonrpclib
from datetime import datetime

class sms_template(models.Model):
    _name = "sms.template"

    name = fields.Char("Nombre", required=True)
    text = fields.Text("Texto", help="Escribir aquí el texto del mensaje. Se pueden usar aquí expresiones de campos")
    res_model = fields.Many2one("ir.model", string="Recurso", required=True)
    dest = fields.Char("Destinatario", help="Escribir aquí la expresión para obtener el número del destinatario, se pueden usar expresiones de campos", default="${object.mobile}")
    ref_ir_act_window = fields.Many2one('ir.actions.act_window', 'Sidebar action', readonly=True, copy=False,
                                        help="Sidebar action to make this template available on records "
                                             "of the related document model")
    @api.model
    def send_sms(self, res_id):
        Template = self.env["mail.template"]
        text = Template.render_template(self.text, self.res_model, res_id)
        record = self.create({
           'texto': text,
           'dest': numero
        })
        record.send()
        return True

class sms(models.Model):
    _name = "sms.sms"

    text = fields.Text("Texto")
    template_id = fields.Many2one("sms.template", string="Plantilla del mensaje")
    dest = fields.Char("Número (destinatario)")
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('outgoing', 'En proceso'),
        ('success', 'Enviado'),
        ('failed', 'No enviado'),
        ('error', 'Error'),
    ], string="Status", default="pending")
    schedule_date = fields.Datetime("Fecha programada")
    fail_reason = fields.Char(u"Razón del fallo")

    @api.multi
    def action_send(self):
        for rec in self:
            rec.send()
        return True

    @api.model
    def send(self):
        try:
            url = "http://portalsms.dyndns.org/mensajes/webservice/call/jsonrpc2"
            server = jsonrpclib.Server(url)
            resp = server.singleSms("yayforme789@gmail.com", "qwe123", self.dest, self.text)
            self.write({'state':'outgoing'})
        except:
            self.write({'state':'error'})
        return True

    @api.model
    def process_queue(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        messages = self.search(['&',
            ('state','not in',('success','failed','outgoing')),
            '|', 
                ('schedule_date','=',False),
                ('schedule_date','<', now)
        ])
        for msg in messages:
            msg.send()
            self._cr.commit()
        return True
                      
class sms_action(models.Model):
    _name = "ir.actions.server"
    _inherit = ['ir.actions.server']

    @api.model
    def _get_states(self):
        res = super(sms_action, self)._get_states()
        res.insert(0, ('sms', 'Enviar SMS'))
        return res

    sms_template = fields.Text("Plantilla del SMS", required=True)

    @api.model    
    def run_action_sms(self, action, eval_context=None):
        self.sms_template.send_sms(self._context.get("active_id"))
        return True
