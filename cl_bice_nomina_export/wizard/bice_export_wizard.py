from odoo import models, fields


class BiceExportWizard(models.TransientModel):
    _name = 'bice.export.wizard'
    _description = 'Exportación archivo proveedores BICE'

    file_data = fields.Binary("Archivo BICE Proveedores", readonly=True)
    file_name = fields.Char("Nombre de archivo", readonly=True)
