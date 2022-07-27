# -*- coding: utf-8 -*-
{
    'name': "opens_buk_import",

    'summary': """
        Servicios y vistas para buscar datos desde el servicio ‘BUK’.""",

    'version': '1.0',
    'author': 'Open Solutions',
    'description': """
        Servicios y vistas para buscar datos desde el servicio ‘BUK’.
     """,
    'license': 'OPL-1',
    'website': 'https://www.opens.cl',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account_accountant', 'account', 'analytic'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/tree.xml',
        'views/buk_settings.xml',
        'views/account_analytic.xml'
    ],

}