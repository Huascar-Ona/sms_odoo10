# -*- coding: utf-8 -*-
{
    'name': "SMS SmartSend",

    'summary': """
    Módulo para envío de SMS SmartSend
""",

    'description': """
    """,

    'author': "SmartSend",
    'website': "http://www.smartsend.com.mx",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'wizard/quick_send_view.xml',
        'wizard/sms_credit.xml',
        'sms_view.xml',
        'menus.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}
