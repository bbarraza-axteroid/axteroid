from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import io
import csv
from datetime import datetime


class BiceExportWizard(models.TransientModel):
    _name = 'bice.export.wizard'
    _description = 'Exportación archivo proveedores BICE'

    file_data = fields.Binary("Archivo BICE Proveedores", readonly=True)
    file_name = fields.Char("Nombre de archivo", readonly=True)

    def action_generate(self):
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            raise UserError("No se encontraron pagos seleccionados.")

        batch_payments = self.env['account.batch.payment'].browse(active_ids)

        if not all(batch.journal_id.bank_id.bic == 'BICECLRM' for batch in batch_payments):
            raise UserError("Todos los pagos deben tener un banco con BIC BICECLRM.")

        output = io.StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_NONE, lineterminator='\n', quotechar='')

        for batch in batch_payments:
            for payment in batch.payment_ids:
                partner = payment.partner_id
                cuenta = partner.bank_ids.filtered(lambda b: b.acc_type == 'iban' or b.acc_number)
                if not cuenta:
                    raise UserError(f"El proveedor '{partner.name}' no tiene cuenta bancaria configurada.")
                cuenta = cuenta[0]

                writer.writerow([
                    payment.company_id.vat or '',              # RUT ordenante
                    '',                                        # RUT apoderado (vacío)
                    datetime.today().strftime('%d-%m-%Y'),    # Fecha proceso
                    payment.payment_reference or '',          # Referencia
                    partner.name[:40],                        # Nombre proveedor
                    cuenta.acc_number,                        # Cuenta proveedor
                    'CC',                                     # Tipo cuenta (fijo)
                    'CLP',                                    # Moneda (fijo)
                    int(payment.amount),                      # Monto
                    '',                                        # Email (vacío)
                    '',                                        # Descripción adicional
                ])

        output.seek(0)
        file_content = output.read().encode('utf-8-sig')  # BOM para compatibilidad Excel

        filename = f"bice_proveedores_{datetime.today().strftime('%Y%m%d')}.csv"

        self.file_data = base64.b64encode(file_content)
        self.file_name = filename

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bice.export.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
