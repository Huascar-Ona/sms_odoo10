# -*- coding: utf-8 -*-
from odoo import http
from odoo import models

class SmsController(http.Controller):
    
    @http.route('/api/on_update/', auth='public', type='json', methods=['POST'], csrf=False)
    def update_status(self, db, login, password, status, res_id, port):
        uid = http.request.session.authenticate(db, login, password)
        if not uid:
            raise Exception("Login failed")
        Sms = http.request.env["sms.sms"]
        state = 'success' if status == 1 else 'failed'
        sms = Sms.browse(res_id)
        sms.write({'state': state, 'port': port})
        credit = http.request.env["sms.credit"].search([('user_id', '=', sms.create_uid.id),('state','=','active')])
        if status == 1:
            credit.discount()
        else:
            credit.refund()
        return "ok"

    @http.route('/api/on_receive', auth='public', type='json', methods=['POST'], csrf=False)
    def receive_sms(self, db, login, password, text, recv_date, res_id):
        uid = http.request.session.authenticate(db, login, password)
        if not uid:
           raise Exception("Login failed")
        Reply = http.request.env["sms.reply"]
        Reply.create({
            'sms_id': res_id,
            'recv_date': recv_date,
            'text': text
        })
        return "ok"
