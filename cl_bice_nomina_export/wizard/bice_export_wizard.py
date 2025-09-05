from odoo import models, fields, api
import base64
import io
import csv
from datetime import datetime

class BiceExportWizard(models.TransientModel):
    _name = "bice.export.wizard"
    _description = "Exportar archivo Proveedores Banco BICE"

    archivo = fields.Binary("Archivo", readonly=True)
    nombre = fields.Char("Nombre", readonly=True, default="proveedores.csv")

    def action_export_bice_nomina(self):
        """Genera el archivo CSV para BICE Proveedores y lo retorna en el wizard"""
        batch = self.env['account.batch.payment'].browse(self._context.get('active_id'))
        if not batch:
            return

        # Buffer CSV en memoria
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=';', quoting=csv.QUOTE_MINIMAL)

        # Recorrer pagos y escribir líneas
        for payment in batch.payment_ids:
            partner = payment.partner_id
            row = [
                partner.name or "",
                partner.vat or "",
                payment.amount or 0.0,
                "CTA CORRIENTE",  # en duro como pediste
                partner.bank_ids[:1].acc_number if partner.bank_ids else "",
            ]
            writer.writerow(row)

        # Contenido CSV
        csv_content = buffer.getvalue()
        buffer.close()

        # Convertir a base64 para el Binary
        archivo_binario = base64.b64encode(csv_content.encode("utf-8"))

        # Asignar archivo y nombre en duro
        self.write({
            "archivo": archivo_binario,
            "nombre": "proveedores.csv"
        })

        # Retornar vista del wizard con archivo cargado
        return {
            "type": "ir.actions.act_window",
            "res_model": "bice.export.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }
