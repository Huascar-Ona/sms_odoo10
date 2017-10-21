# -*- coding: utf-8 -*-
from odoo import api,fields,models

class res_users(models.Model):
    _inherit = 'res.users'

    parent_id = fields.Many2one("res.users", string="Padre", store=True)
    balance = fields.Integer(string="Saldo", store=True)
    amount = fields.Integer(string="Cantidad")

class sms_users(models.Model):
    _name = "sms.users"

    @api.onchange('user')
    def _get_balance(self):
        if self.user:
            self.balance = self.user.balance

    @api.multi
    def shady(self):
        users = self.env['res.users']
        hijos = users.search([('parent_id','=',self.user.id)])

        print hijos

        lines = []
        for hijo in hijos:
            lines.append({
                'user': hijo.id,
                'balance': hijo.balance,
                'amount': hijo.amount
            })

        print lines
        self.write({'sons_lines': [(0,0,vals) for vals in lines]})

        return {
                'type':'ir.action.act_window',
                'res_model': 'sms.users.line',
                'res_id': self.id,
                'view_mode':'form',
                'view_type':'form',
                'name': 'view.form.users.wizard',
                'target': 'inline'
            }

    user = fields.Many2one("res.users", string="Usuario Padre")
    sons_lines = fields.One2many("sms.users.lines", "user", string="Lineas")
    balance = fields.Integer(string="Saldo", default=_get_balance, store=True)
    amount = fields.Integer(string="Cantidad")


class sms_user_lines(models.Model):
    _name = 'sms.users.lines'

    user = fields.Many2one("res.users", string="Hijo")
    balance = fields.Integer(string="Saldo")
    amount = fields.Integer(string="Cantidad")

class sms_recharge_history(models.Model):
    _name = 'sms.recharge.history'

    beneficiary = fields.Many2one("res.users", "Usuario", store="True")
    amount = fields.Many2one(string="Monto", store="True")
