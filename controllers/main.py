# -*- coding: utf-8 -*-
from odoo import http
from odoo import models

class SmsController(http.Controller):
    
     @http.route('/api/telegram/', auth='user', type='json', methods=['POST'], csrf=False)
     def update_status(self, status, res_id):
         Sms = http.request.env["sms.sms"]
         state = 'success' if status == 1 else 'failed'
         Sms.browse(res_id).write({'state': state})
         return "ok"
