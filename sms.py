# -*- coding: utf-8 -*-
from odoo import api,fields,models
import jsonrpclib
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class sms_template(models.Model):
    _name = "sms.template"
    _description = "Plantilla de mensaje SMS"

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
    _order = "create_date desc"
    _description ="Mensaje de texto SMS"

    name = fields.Char(u"Identificador de envío")
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
    port = fields.Integer("Puerto")

    @api.multi
    def action_send(self):
        for rec in self:
            rec.send()
        return True

    @api.model
    def send(self):
        try:
            credit = self.env["sms.credit"].search([('user_id','=',self._uid),('state','=','active')], limit=1)
            if not credit:
                credit = self.env["sms.credit"].search([('user_id','=',self._uid),('state','=','paid')], order='create_date asc', limit=1)
                if not credit:
                    raise Exception("Saldo insuficiente")
                credit.write({'state': 'active'})
            credit.check_credit()
            url = "http://187.190.106.248:8000/mensajes/webservice/call/jsonrpc2"
            server = jsonrpclib.Server(url)
            span = self.port if self.port > 0 else None
            resp = server.singleSms(username="odoo", password="o9o9deo9", numero=self.dest, mensaje=self.text, custom_id=self.id, span=span)
            self.write({'state':'outgoing', 'fail_reason':''})
            credit.add_pending()
        except Exception as ex:
            self.write({'state':'error', 'fail_reason': ex.message or repr(ex)})
        return True

    @api.model
    def process_queue(self):
        _logger.info("Processing SMS queue")
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

class sms_reply(models.Model):
    _name = "sms.reply"
    _order = "recv_date desc"

    text = fields.Text("Texto")
    sms_id = fields.Many2one("sms.sms", "Mensaje siendo respondido")
    sms_id_create_uid = fields.Many2one("res.users", "Usuario", related="sms_id.create_uid", store=True)
    sms_id_text = fields.Text("Texto del mensaje siendo respondido", related="sms_id.text")
    number = fields.Char("Remitente", related="sms_id.dest", store=True)
    name = fields.Char(u"Identificador de envío", related="sms_id.name", store=True)
    recv_date = fields.Char(u"Fecha de recepción")

class sms_reply_wizard(models.TransientModel):
    _name = "sms.reply.wizard"

    text = fields.Text("Texto")
    sms_reply_id = fields.Many2one("sms.reply", "SMS siendo respondido")

    @api.model
    def default_get(self, fields):
        res = super(sms_reply_wizard, self).default_get(fields)
        res['sms_reply_id'] = self.env.context.get("active_id")
        return res

    @api.one
    def send(self):
        self.env["sms.sms"].create({
            'text': self.text,
            'dest': self.sms_reply_id.number,
            'name': self.sms_reply_id.name,
            'port': self.sms_reply_id.sms_id.port
        })
        return True

class sms_credit(models.Model):
    _name = "sms.credit"
    _description = "Credito SMS"
    
    state = fields.Selection([('paid','Pagado'),('active','En uso'),('finished','Agotado')], string="Estado", default='paid')
    amount = fields.Integer("Pagados")
    used = fields.Integer("Usados")
    remaining = fields.Integer("Restantes")
    pending = fields.Integer("Pendientes")
    user_id = fields.Many2one("res.users", string="Usuario")

    @api.model
    def check_credit(self):
        if self.remaining - self.pending > 0:
            return True
        else:
            raise Exception("Saldo insuficiente")
        
    @api.model
    def add_pending(self):
        self.pending += 1
        self.remaining -= 1
        
    @api.model
    def discount(self):
        if self.pending > 0 and self.remaining > 0:
            self.pending -= 1
            self.used += 1
            if self.remaining == 0:
                self.state = 'finished'
    
    @api.model
    def refund(self):
         self.pending -= 1
         self.remaining += 1
                          
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
