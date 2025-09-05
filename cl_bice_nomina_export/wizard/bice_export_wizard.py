from odoo import models, fields, api
import base64
import csv
from io import StringIO

class BiceExportWizard(models.TransientModel):
    _name = 'bice.export.wizard'
    _description = 'Exportar archivo Proveedores Banco BICE'

    batch_id = fields.Many2one(
        'account.batch.payment',
        string='Batch',
        required=True,
        readonly=True,
    )

    def action_generate(self):
        # Generar el contenido del CSV
        csv_buffer = StringIO()
        writer = csv.writer(csv_buffer, delimiter=';', quoting=csv.QUOTE_MINIMAL)

        # Cabecera (ajústala según layout real del BICE)
        writer.writerow(['Rut', 'Nombre', 'Cuenta', 'Monto'])

        # Detalle de pagos
        for payment in self.batch_id.payment_ids:
            partner = payment.partner_id
            writer.writerow([
                partner.vat or '',
                partner.name or '',
                payment.partner_bank_id.acc_number or '',
                "{:.2f}".format(payment.amount),
            ])

        csv_content = csv_buffer.getvalue()
        csv_buffer.close()

        # Guardar como attachment vinculado al lote
        attachment = self.env['ir.attachment'].create({
            'name': 'proveedores_bice.csv',
            'type': 'binary',
            'datas': base64.b64encode(csv_content.encode('utf-8')),
            'res_model': 'account.batch.payment',
            'res_id': self.batch_id.id,
            'mimetype': 'text/csv',
        })

        # Opcional: mensaje en el chatter del lote
        self.batch_id.message_post(
            body="Se generó el archivo BICE Proveedores",
            attachment_ids=[attachment.id]
        )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.batch.payment',
            'view_mode': 'form',
            'res_id': self.batch_id.id,
        }
