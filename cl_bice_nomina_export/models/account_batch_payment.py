# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError
import base64
import io
import csv
import re
import unicodedata
from datetime import date


def _strip_accents(text):
    if not text:
        return ''
    # NFKD para separar tildes y luego eliminar marcas diacríticas
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(ch for ch in nfkd if not unicodedata.combining(ch))


def _only_ascii_letters_digits_space(text):
    # deja solo letras/números/espacio; elimina ., - y otros signos
    text = _strip_accents(text)
    text = text.replace('Ñ', 'N').replace('ñ', 'n')
    return re.sub(r'[^A-Za-z0-9 ]+', '', text)


def _sanitize_name(raw):
    # hasta 40, sin puntos, guion ni tildes (según pauta)
    name = _only_ascii_letters_digits_space(raw or '')
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:40]


def _sanitize_rut(raw):
    # hasta 11, sin puntos ni guion. Dejar dígitos y K
    val = (raw or '').upper()
    val = re.sub(r'[^0-9Kk]', '', val)
    val = val.replace('K', 'K')  # normaliza K
    return val[:11]


def _sanitize_account_number(raw):
    # CCA suele esperar números. Quitamos no-dígitos.
    acc = re.sub(r'\D+', '', (raw or ''))
    return acc[:17]


def _sanitize_bank_code(raw):
    # Código CCA proviene de res.bank.code_cca (string numérica). Fallback '0'
    code = re.sub(r'\D+', '', (raw or ''))
    return code if code else '0'


def _map_account_type(partner_bank):
    """
    Tipo de Cuenta CCA:
      1 = Vista
      2 = Ahorro
      3 = Corriente o Cuenta RUT
    Si no hay tipo, usamos 3 por defecto (como pactamos).
    Si tienes un campo propio (p.ej. x_bice_account_type) puedes mapearlo acá.
    """
    # Intento de mapeo por nombre del banco/cuenta si existiera algo
    # Por defecto fijo = 3 (Corriente/RUT)
    return '3'


def _sanitize_amount_clp(amount):
    # Entero sin separadores ni decimales
    if amount is None:
        return '0'
    # Redondeo al entero más cercano
    return str(int(round(amount)))


def _sanitize_email(email):
    if not email:
        return ''
    # El formato indicado permite letras/números (sin Ñ), y . - _
    email = _strip_accents(email)
    email = email.replace('Ñ', 'N').replace('ñ', 'n')
    email = re.sub(r'[^A-Za-z0-9@\.\-_]+', '', email)
    return email[:50]


def _sanitize_factura(ref):
    # Obligatorio, hasta 15, sin espacios
    ref = (ref or '').strip()
    if not ref:
        ref = 'SINFACTURA'
    ref = _strip_accents(ref)
    ref = ref.replace(' ', '')
    # Dejar solo letras/números
    ref = re.sub(r'[^A-Za-z0-9]+', '', ref)
    if not ref:
        ref = 'SINFACTURA'
    return ref[:15]


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    def action_export_bice_nomina(self):
        """
        Exporta CSV de Proveedores para Banco BICE (CCA), sin encabezados,
        en el siguiente orden de columnas:
          1 Nombre Titular
          2 Rut Titular
          3 Cuenta Titular
          4 Monto
          5 Banco (código CCA)
          6 Tipo de Cuenta (1 Vista, 2 Ahorro, 3 Corriente/RUT)
          7 Moneda (0)
          8 Oficina Origen (1)
          9 Oficina Destino (1)
          10 Factura (obligatorio, sin espacios, <=15)
          11 Mail Beneficiario (opcional)
        Además, guarda el archivo como adjunto del lote y dispara la descarga.
        """
        self.ensure_one()

        if self.payment_type != 'outbound':
            raise UserError(_("Este layout aplica solo a pagos salientes (outbound)."))

        if not self.payment_ids:
            raise UserError(_("No hay pagos en este lote."))

        # Armado del CSV
        buf = io.StringIO(newline='')
        writer = csv.writer(buf, delimiter=',', quoting=csv.QUOTE_MINIMAL)

        for pay in self.payment_ids:
            partner = pay.partner_id

            # Nombre
            nombre = _sanitize_name(partner.name)

            # RUT
            rut = _sanitize_rut(partner.vat)

            # Cuenta y banco del beneficiario
            # Tomamos la cuenta bancaria del partner (si tu flujo usa un campo específico cámbialo aquí).
            partner_bank = getattr(pay, 'partner_bank_id', False) or (partner.bank_ids[:1] if partner.bank_ids else False)
            if not partner_bank:
                raise UserError(_("El beneficiario %s no tiene cuenta bancaria configurada.") % (partner.display_name,))
            cuenta = _sanitize_account_number(partner_bank.acc_number)

            # Código CCA del banco (res.bank.code_cca)
            bank = partner_bank.bank_id
            if not bank:
                raise UserError(_("La cuenta del beneficiario %s no tiene banco asignado.") % (partner.display_name,))
            banco_cca = _sanitize_bank_code(getattr(bank, 'code_cca', ''))

            # Tipo cuenta (1/2/3)
            tipo_cta = _map_account_type(partner_bank)

            # Monto CLP entero
            monto = _sanitize_amount_clp(pay.amount)

            # Campos fijos según pauta
            moneda = '0'
            ofi_origen = '1'
            ofi_destino = '1'

            # Factura (obligatorio)
            # Usamos ref/communication del pago como origen; si no, SINFACTURA
            raw_ref = (getattr(pay, 'ref', '') or getattr(pay, 'communication', '') or '')
            factura = _sanitize_factura(raw_ref)

            # Mail (opcional)
            email = _sanitize_email(partner.email)

            row = [
                nombre, rut, cuenta, monto, banco_cca, tipo_cta,
                moneda, ofi_origen, ofi_destino, factura, email
            ]
            writer.writerow(row)

        csv_data = buf.getvalue()
        buf.close()

        # Nombre "duro" como pediste
        filename = 'proveedores.csv'

        # Guardar como adjunto del lote (queda en el clip)
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'res_model': 'account.batch.payment',
            'res_id': self.id,
            'type': 'binary',
            'mimetype': 'text/csv',
            'datas': base64.b64encode(csv_data.encode('utf-8')),
        })

        # Y también disparar descarga directa
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=1',
            'target': 'self',
        }
