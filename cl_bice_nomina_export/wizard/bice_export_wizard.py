from odoo import models, fields
import base64
from io import StringIO


class BiceExportWizard(models.TransientModel):
    _name = "bice.export.wizard"
    _description = "Exportar archivo Proveedores Banco BICE"

    file_data = fields.Binary("Archivo", readonly=True, required=False)
    file_name = fields.Char("Nombre archivo", readonly=True)

    def action_export(self):
        """
        Genera un archivo CSV con el layout BICE y lo devuelve para descarga inmediata.
        """

        # 🔹 Aquí deberías reemplazar por la lógica real con los pagos
        output = StringIO()
        # Ejemplo de línea (Rut, Cuenta, Monto, Moneda)
        output.write("12345678,98765432,10000,CLP\n")

        csv_content = output.getvalue()
        output.close()

        # Codificar archivo en base64
        self.write({
            "file_data": base64.b64encode(csv_content.encode("utf-8")),
            "file_name": "bice_nomina.csv",
        })

        # Retornar acción que fuerza la descarga
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/?model={self._name}&id={self.id}&field=file_data&download=true&filename={self.file_name}",
            "target": "self",
        }
