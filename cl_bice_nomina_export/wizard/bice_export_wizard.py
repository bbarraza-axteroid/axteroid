# -*- coding: utf-8 -*-
import base64
import csv
import io
import re
import unicodedata

from odoo import _, api, fields, models
from odoo.exceptions import UserError

RUT_CLEAN_RE = re.compile(r"[^0-9Kk]")
ONLY_DIGITS_RE = re.compile(r"\D")


def _strip_accents(text: str) -> str:
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])


def _clean_name(name: str) -> str:
    s = (name or "").strip()
    s = _strip_accents(s).replace("Ñ", "N").replace("ñ", "n")
    s = re.sub(r"[.\-]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s[:40]


def _clean_rut(vat: str) -> str:
    """
    Acepta RUT con o sin puntos/guión y DV.
    Devuelve solo dígitos + K (máx 11).
    """
    s = (vat or "").upper()
    s = s.replace(".", "").replace("-", "")
    s = RUT_CLEAN_RE.sub("", s)
    return s[:11]


def _clean_acc_number(num: str) -> str:
    return ONLY_DIGITS_RE.sub("", num or "")[:17]


class AccountBatchPayment(models.Model):
    _inherit = "account.batch.payment"

    def _row_from_payment_bice(self, pay, idx):
        """Construye una fila para el layout de Proveedores BICE (CSV).
        Ajusta aquí el orden/valores si el banco te pide cambios.
        """
        partner = pay.partner_id
        pb = pay.partner_bank_id

        # Validaciones básicas y MENSAJES CLAROS
        if not pb:
            raise UserError(_(f"Pago {pay.name}: el proveedor {partner.display_name} no tiene "
                              f"cuenta bancaria seleccionada en el pago."))

        if not partner.vat:
            raise UserError(_(f"{partner.display_name}: falta RUT (campo VAT) en el contacto."))

        name = _clean_name(partner.name)
        rut = _clean_rut(partner.vat)
        if not rut:
            raise UserError(_(f"{partner.display_name}: RUT inválido."))

        acc_number = _clean_acc_number(pb.acc_number)
        if not acc_number:
            raise UserError(_(f"{partner.display_name}: número de cuenta inválido."))

        bank = pb.bank_id
        bank_code = (bank.l10n_cl_sbif_code or bank.bic or "").strip()
        if not bank_code:
            raise UserError(_(f"{partner.display_name}: Banco sin código CCA/CMF "
                              f"(configúralo en el maestro del banco)."))

        # Tipo de cuenta: ajusta si el BICE exige código distinto
        # (deja fijo por ahora si así te lo aceptó el banco)
        tipo_cuenta = "CC"  # ejemplo: "CC" corriente; cambia a "VISTA"/"CTE" si tu layout lo requiere

        # Moneda (siempre CLP para Proveedores)
        moneda = "CLP"

        # Monto entero (sin decimales)
        amount = int(round(pay.amount))
        if amount <= 0:
            raise UserError(_(f"{partner.display_name}: el monto debe ser positivo."))

        # Referencia / factura (tómala de ref/communication/move/ref)
        ref = pay.ref or pay.communication or pay.move_id.ref or ""
        ref = _strip_accents(ref).replace("\n", " ").strip()

        # Email (opcional; déjalo vacío si no aplica)
        email = (partner.email or "").strip()

        # ------------- LAYOUT CSV (sin encabezado) ----------------
        # OJO: Este es un ejemplo base (11 columnas). Ajusta el orden si tu archivo lo exige distinto.
        row = [
            rut,                # 1 RUT Proveedor
            name,               # 2 Nombre Proveedor
            acc_number,         # 3 Nº Cuenta
            tipo_cuenta,        # 4 Tipo Cuenta (p.ej. CC)
            bank_code,          # 5 Banco (CCA/CMF)
            moneda,             # 6 Moneda (CLP)
            str(amount),        # 7 Monto (entero)
            ref,                # 8 Referencia/Factura
            "",                 # 9 Campo libre (deja vacío si no aplica)
            "",                 # 10 Campo libre
            email,              # 11 Email (opcional)
        ]
        return row

    def export_bice_proveedores_file(self):
        """Acción desde el lote que genera el archivo y abre el wizard con el binario."""
        self.ensure_one()

        if self.payment_type != "outbound":
            raise UserError(_("Esta nómina aplica solo a pagos de salida (proveedores)."))

        payments = self.payment_ids
        if not payments:
            raise UserError(_("El lote no contiene pagos."))

        # Generar CSV delimitado por ; sin encabezado
        buf = io.StringIO(newline="")
        writer = csv.writer(buf, delimiter=";")

        for i, p in enumerate(payments, start=1):
            writer.writerow(self._row_from_payment_bice(p, i))

        content = buf.getvalue()
        # IMPORTANTE: cambia la codificación si BICE pide ISO-8859-1/Latin-1
        raw = content.encode("utf-8-sig", errors="ignore")
        b64 = base64.b64encode(raw)
        fname = f"bice_proveedores_{fields.Date.context_today(self)}.csv"

        # Crear wizard con el binario para que el usuario descargue
        wiz = self.env["bice.export.wizard"].create({
            "file_data": b64,
            "file_name": fname,
        })

        return {
            "name": _("Exportar Nómina BICE"),
            "type": "ir.actions.act_window",
            "res_model": "bice.export.wizard",
            "view_mode": "form",
            "target": "new",
            "res_id": wiz.id,

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
