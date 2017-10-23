# -*- coding: utf-8 -*-
from odoo import api,fields,models
from odoo.exceptions import Warning

class res_users(models.Model):
    _inherit = 'res.users'

    parent_id = fields.Many2one("res.users", string="Padre")
    balance = fields.Integer("Saldo")
    amount = fields.Integer("Cantidad")

class sms_users(models.TransientModel):
    _name = "sms.users"

    @api.onchange('user')
    def _get_balance(self):
        if self.user:
            self.balance = self.user.balance

    @api.multi
    def transfer(self):
        if not self.user:
            self.user = self.env.user
        Users = self.env['res.users']
        for line in self.sons_lines:
            self.user.balance -= line.amount
            if self.user.balance < 0 :
                raise Warning("El usuario padre no cuenta con suficiente saldo")
            Users.browse(line.user.id).write({'balance': line.user.balance + line.amount})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }

    @api.model
    def default_get(self, fields):
        res = super(sms_users, self).default_get(fields)
        users = self.env['res.users']
        hijos = users.search([('parent_id','=',self.env.uid)])

        lines = []
        for hijo in hijos:
            lines.append({
                'user': hijo.id,
                'balance': hijo.balance,
                'amount': hijo.amount
            })

        res['sons_lines'] =  [(0,0,vals) for vals in lines]
        res['user'] = self.env.uid
        return res

    user = fields.Many2one("res.users", string="Usuario Padre")
    sons_lines = fields.One2many("sms.users.lines", "wizard_id", string="Lineas")
    balance = fields.Integer(string="Saldo", default=_get_balance, store=True)
    amount = fields.Integer(string="Cantidad")


class sms_user_lines(models.TransientModel):
    _name = 'sms.users.lines'

    wizard_id = fields.Many2one("sms.users", string="Wizard")
    user = fields.Many2one("res.users", string="Hijo", required=True)
    balance = fields.Integer(string="Saldo")
    amount = fields.Integer(string="Cantidad")

class sms_recharge_history(models.Model):
    _name = 'sms.recharge.history'

    beneficiary = fields.Many2one("res.users", "Usuario", store="True")
    amount = fields.Many2one(string="Monto", store="True")
