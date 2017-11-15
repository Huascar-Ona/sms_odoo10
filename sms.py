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
            user = self.env["res.users"].browse(self.create_uid.id)
            if user.balance <= 0:
                raise Exception("Saldo insuficiente")
            url = self.env["ir.config_parameter"].get_param("sms.url")
            server = jsonrpclib.Server(url)
            span = self.port if self.port > 0 else None
            resp = server.singleSms(
                username=self.env["ir.config_parameter"].get_param("sms.user"),
                password=self.env["ir.config_parameter"].get_param("sms.password"),
                numero=self.dest, mensaje=self.text, custom_id=self.id, span=span)
            user.sudo().write({'balance': user.balance - 1})
            self.write({'state':'outgoing', 'fail_reason':''})
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

class sms_credit(models.TransientModel):
    _name = "sms.credit"
    _description = "Credito SMS"

    user = fields.Many2one("res.users", string="Usuario")
    balance = fields.Integer(string="Saldo", compute="_get_balance", store="True")
    amount = fields.Integer(string="Abono")

    @api.multi
    def action_credit(self):
        history = self.env["sms.recharge.history"]
        credit = self.user.balance + self.amount

        history.create({
            "beneficiary": self.user.id,
            "amount": self.amount
        })

        self.user.write({"balance": credit})
        return True

    @api.onchange('user')
    def _get_balance(self):
        if self.user:
            self.balance = self.user.balance
        else:
            self.balance = 0

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

class sms_contact(models.Model):
    _name = "sms.contact"
    _description = "Contacto"

    name = fields.Char(u"Identificador de envío")
    telefono = fields.Char(u"Número de Teléfono")
    list_id = fields.Many2one(
        'sms.list', string='Nombre de Lista',
        ondelete='cascade', required=True, default=lambda self: self.env['sms.list'].search([], limit=1, order='id desc'))

class sms_list(models.Model):
    _name = "sms.list"
    _description = "Lista de Contactos"

    name = fields.Char(string="Nombre de Lista")
    contact_nbr = fields.Integer(compute="_compute_contact_nbr", string='Numero de Contactos')

    def _compute_contact_nbr(self):
        contacts_data = self.env['sms.contact'].read_group([('list_id', 'in', self.ids)], ['list_id'], ['list_id'])
        mapped_data = dict([(c['list_id'][0], c['list_id_count']) for c in contacts_data])
        for mailing_list in self:
            mailing_list.contact_nbr = mapped_data.get(mailing_list.id, 0)
