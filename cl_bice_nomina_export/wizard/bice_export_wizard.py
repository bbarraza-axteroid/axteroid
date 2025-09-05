from odoo import models, fields, api
import base64
import csv
import io

class BiceExportWizard(models.TransientModel):
    _name = "bice.export.wizard"
    _description = "Exportar archivo Proveedores Banco BICE"

    archivo = fields.Binary("Archivo", readonly=True)
    nombre = fields.Char("Nombre", default="proveedores.csv", readonly=True)

    def action_export(self):
        """Generar CSV de prueba y mostrar link de descarga"""

        # Crear CSV temporal
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')

        # Cabecera de ejemplo (ajusta al formato de BICE)
        writer.writerow(["RUT", "Nombre", "Banco", "Cuenta", "Monto"])

        # Datos de ejemplo (en producción, usar los pagos del batch)
        writer.writerow(["11111111-1", "Proveedor Demo", "BICE", "12345678", "10000"])

        # Codificar a base64
        file_content = base64.b64encode(output.getvalue().encode("utf-8"))

        # Guardar en los campos del wizard
        self.write({
            "archivo": file_content,
            "nombre": "proveedores.csv"
        })

        # Volver a abrir el wizard con el archivo ya disponible
        return {
            "type": "ir.actions.act_window",
            "res_model": "bice.export.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }
