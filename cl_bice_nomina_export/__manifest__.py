{
    'name': 'Exportador BICE Nómina Proveedores',
    'version': '1.0',
    'summary': 'Exportación de nómina proveedores Banco BICE desde pagos por lote',
    'category': 'Accounting',
    'author': 'Branco Barraza',
    'depends': ['account_batch_payment'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/bice_export_wizard_views.xml',
        'views/account_batch_payment_views.xml',
    ],
    'installable': True,
}
