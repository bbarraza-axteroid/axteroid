{
    "name": "CL: Exportador Nómina Banco BICE (Proveedores)",
    "version": "17.0.2.1.0",
    "summary": "Genera archivo CSV (layout BICE Proveedores) desde Pagos en Lote (Tipo cuenta fijo Corriente).",
    "author": "BrancoBarraza",
    "website": "",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_bank_views.xml",
        "views/account_batch_payment_views.xml",
        "wizard/bice_export_wizard_views.xml"
    ],
    "application": false
    'name': 'Exportador BICE Nómina Proveedores',
    'version': '1.0',
    'summary': 'Exportación de nómina proveedores Banco BICE desde pagos por lote',
    'category': 'Accounting',
    'author': 'Branco_Barraza',
    'depends': ['account_batch_payment'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/bice_export_wizard_views.xml',
        'views/account_batch_payment_views.xml',
    ],
    'installable': True,
}
