# -*- coding: utf-8 -*-
import logging
from odoo import fields, models, _


_logger = logging.getLogger(__name__)


class ProductAVCOReportXlsx(models.AbstractModel):
    _name = 'report.product_avco_report.product_avco_report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, objects):
        """ Draw the excel report """
        move_obj = self.env['stock.move']
        date_to = fields.Datetime.from_string(data['form']['date_to'])
        location_ids = data['form']['location_ids']

        sheet = workbook.add_worksheet('sheet')

        header_format = workbook.add_format({
            'bold': 1,
            'border': 2,
            'align': 'left',
            'valign': 'vcenter',
            'color': 'blue',
            })

        left_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'bold': 1,
            'border': 1,
            'bg_color': 'silver',
            'color': 'blue',

        })

        center_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'bold': 1,
            'border': 1,
            'bg_color': 'silver',

        })

        sheet.set_column('A:A', 20)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:C', 30)
        sheet.set_column('D:D', 10)
        sheet.set_column('E:E', 10)
        sheet.set_column('F:F', 20)
        sheet.set_column('G:G', 15)
        sheet.set_column('H:H', 15)
        sheet.set_column('I:I', 20)
        sheet.set_column('J:J', 20)
        sheet.set_column('K:K', 10)
        sheet.set_column('L:L', 10)
        sheet.set_column('M:M', 10)

        sheet.merge_range("A1:L1", _("Product AVCO Per Location Report"), header_format)
        sheet.write("A3", _("Internal Reference"), center_format)
        sheet.write("B3", _("Name"), center_format)
        sheet.write("C3", _("Attribute values"), center_format)
        sheet.write("D3", _("Sale Price"), center_format)
        sheet.write("E3", _("Cost"), center_format)
        sheet.write("F3", _("Quantity On Hand"), center_format)
        sheet.write("G3", _("AVCO(unit)"), center_format)
        sheet.write("H3", _("Last PO Price"), center_format)
        sheet.write("I3", _("Last Landed Cost"), center_format)
        sheet.write("J3", _("Unit Of Measure"), center_format)
        sheet.write("K3", _("Barcode"), center_format)

        domain = ['|', ('location_id', 'in', location_ids), ('location_dest_id', 'in', location_ids),
                  ('state', '=', 'done')]

        if date_to:
            domain.append(('date', '<=', date_to))

        all_move_lines = move_obj.sudo().search(domain)
        locations = self.env['stock.location'].browse(location_ids)
        row = 3
        col = 0
        for location in locations:
            location_move_lines = all_move_lines.filtered(lambda l:l.location_id.id == location.id or
                                                                   l.location_dest_id.id == location.id)
            products = location_move_lines.sudo().mapped('product_id')
            sheet.merge_range(row, col, row, col+10, _(location.display_name), left_format)
            row += 1

            for product in products:
                sheet.write(row, col, _(product.default_code))
                sheet.write(row, col+1, _(product.name))
                sheet.write(row, col+2, _(product.attribute_value_ids.mapped('display_name')))
                sheet.write(row, col+3, _(product.lst_price))
                sheet.write(row, col+4, _(product.standard_price))
                product_qty_onhand = self.get_product_quantity_onhand(location.id, date_to, product.id)
                sheet.write(row, col+5, _(product_qty_onhand))

                product_average_cost = self.get_product_product_average_cost(location.id, date_to,
                                                                             product.id, product_qty_onhand)

                sheet.write(row, col+6, _(product_average_cost))
                last_purchase_order = self.env['purchase.order.line'].search([('product_id', '=', product.id),
                                                                              ('company_id', '=', self.env.user.company_id.id),
                                                                              ('state', 'in', ['done', 'purchase'])],
                                                                             order="id desc", limit=1)

                sheet.write(row, col+7, _(last_purchase_order.price_unit if last_purchase_order else 0.0))

                last_landed_cost = self.env['stock.valuation.adjustment.lines'].search([('product_id', '=', product.id),
                                                                                        ('move_id.location_dest_id', '=',location.id)],
                                                                                       order="create_date desc", limit=1)
                sheet.write(row, col+8, _(last_landed_cost.additional_landed_cost if last_landed_cost else 0.0))

                sheet.write(row, col+9, _(product.uom_id.name))
                sheet.write(row, col+10, _(product.barcode))

                row += 1
            row += 1

    def get_product_quantity_onhand(self, location_id, date_to, product_id):
        move_obj = self.env['stock.move']

        in_domain = [('product_id', '=', product_id), ('location_dest_id', '=', location_id), ('state', '=', 'done')]

        if date_to:
            in_domain.append(('date', '<=', date_to))
        in_moves = move_obj.sudo().search(in_domain)

        out_domain = [('product_id', '=', product_id), ('location_id', '=', location_id), ('state', '=', 'done')]

        if date_to:
            out_domain.append(('date', '<=', date_to))
        out_moves = move_obj.sudo().search(out_domain)

        qty_on_hand = sum(move.quantity_done for move in in_moves) - sum(move.quantity_done for move in out_moves)

        return qty_on_hand

    def get_product_product_average_cost(self, location_id, date_to, product_id, qty_onhand):
        move_obj = self.env['stock.move']

        in_domain = [('product_id', '=', product_id), ('location_dest_id', '=', location_id), ('state', '=', 'done')]

        if date_to:
            in_domain.append(('date', '<=', date_to))
        in_moves = move_obj.sudo().search(in_domain)

        in_move_values = sum(move.value for move in in_moves)

        out_domain = [('product_id', '=', product_id), ('location_id', '=', location_id), ('state', '=', 'done')]

        if date_to:
            out_domain.append(('date', '<=', date_to))
        out_moves = move_obj.sudo().search(out_domain)
        out_move_values = sum(move.value for move in out_moves)

        product_average_cost = (out_move_values + in_move_values) / qty_onhand if qty_onhand else 0.0
        return product_average_cost
