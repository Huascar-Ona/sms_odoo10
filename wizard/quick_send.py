# -*- coding: utf-8 -*-
from odoo import api,fields,models
import base64

class quick_send_wizard(models.TransientModel):
    _name = "sms.quick_send_wizard"
    _description = "Envio rapido"

    text = fields.Text("Texto")
    dests = fields.Text("Destinatarios", help="Separar por saltos de línea")
    dbfile = fields.Binary("Archivo", help="Puede subir un archivo con los destinatarios")
    schedule_date = fields.Datetime("Fecha programada", help="Cuándo se deben empezar a enviar estos mensajes. Dejar en blanco para enviar en este momento")

    @api.multi
    def action_process(self):
        Sms = self.env["sms.sms"]
        dests = []
        if self.dests:
            for number in self.dests.split("\n"):
                number = number.strip()
                dests.append(number)
        if self.dbfile:
            content = base64.b64decode(self.dbfile)
            for number in content.split("\n"):
                number = number.strip()
                dests.append(number)
        created = []
        for number in dests:    
            if number:
                created.append(Sms.create({
                    'text': self.text,
                    'dest': number
                }))
        return {
            'name': 'SMS',
            'res_model': 'sms.sms',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'list,form',
            'domain': [('id', 'in', [x.id for x in created])]
        }
