# -*- coding: utf-8 -*-
import logging
from odoo import fields, models, _


_logger = logging.getLogger(__name__)


class StockAgingReportXlsx(models.AbstractModel):
    _name = 'report.stock_aging.stock_aging_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, objects):
        """ Draw the excel report """

        sheet = workbook.add_worksheet('sheet')
        max_col = self._generate_headers(workbook, sheet, data['form'])

        all_product_data = self._get_product_data_report(data['form'])
        row = 6
        for product_data in all_product_data:
            col = 0
            sheet.write(row, col, product_data['product'])
            col += 1
            sheet.write(row, col, product_data['0'])
            col += 1
            sheet.write(row, col, product_data['1'])
            col += 1
            sheet.write(row, col, product_data['2'])
            col += 1
            sheet.write(row, col, product_data['3'])
            col += 1
            sheet.write(row, col, product_data['4'])
            col += 1
            sheet.write(row, col, product_data['5'])
            col += 1
            sheet.write(row, col, product_data['6'])
            col += 1
            row += 1


    def _generate_headers(self, workbook, sheet, data):


        sheet.set_column('A:A', 15)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 15)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:E', 15)
        sheet.set_column('F:F', 15)
        sheet.set_column('G:G', 15)
        sheet.set_column('H:H', 15)
        sheet.set_column('I:I', 15)
        sheet.set_column('J:J', 15)

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

        })

        # Header of Report data ,titles

        sheet.merge_range("A1:L1", _("Stock Aging Report"), header_format)
        sheet.write("A3", _("Company:"), header_format)
        sheet.write("B3", data['company_id'][1])
        sheet.write("C3", _("Period Length(Days):"), header_format)
        sheet.write("D3", data['period_length'])
        sheet.write("E3", _("Date:"), header_format)
        sheet.write("F3", data['end_date'])
        sheet.write("A4", _("Location:"), header_format)
        sheet.write("B4", data['location_id'][1])
        sheet.write("C4", _("Product Category:"), header_format)
        sheet.write("D4", data['product_categ_id'][1])
        column_datas = []
        current_period_length = 0

        # Return header Names
        for i in range(0, 6):
            col = str(current_period_length) + "-" + str(current_period_length + data['period_length'])
            current_period_length += data['period_length']
            column_datas.append(col)
        col = "> " + str(current_period_length)
        column_datas.append(col)

        row = 5
        col = 0

        sheet.write(row, col, _('Product'), left_format)
        col += 1

        for column_data in column_datas:
            sheet.write(row, col, column_data, left_format)
            col += 1

        return col

    def _get_product_data_report(self, data):
        all_product_data = []

        if data['product_id']:
            products = self.env['product.product'].browse(data['product_id'][0])
        else:
            products = self.env['product.product'].search([('categ_id', '=', data['product_categ_id'][0])])

        location_id = data['location_id'][0]
        end_date = fields.Datetime.from_string(data['end_date'])
        period_length = data['period_length']

        for product in products:
            quants = self.env['stock.quant'].search([('product_id', '=', product.id),
                                                     ('location_id', '=', location_id),
                                                     ('in_date', '<', end_date)])
            product_data = {}
            product_data['product'] = product.name
            product_data['0'] = 0.0
            product_data['1'] = 0.0
            product_data['2'] = 0.0
            product_data['3'] = 0.0
            product_data['4'] = 0.0
            product_data['5'] = 0.0
            product_data['6'] = 0.0
            for quant in quants:
                quant_moves = self.env['stock.move.line'].search([('product_id', '=', product.id),
                                                        '|',
                                                        ('location_id', '=', location_id),
                                                        ('location_dest_id', '=', location_id),
                                                        ('lot_id', '=', quant.lot_id.id)])
                for move in quant_moves:
                    remaining_quantity = move.qty_done
                    # move is in
                    if move.location_dest_id.id == location_id:
                        date_diff = (end_date - move.date).days
                        if date_diff < 0:
                            date_diff = 0
                        key = min(int(date_diff / period_length), 6)
                        product_data[str(key)] += remaining_quantity
                    # move is out
                    if move.location_id.id == location_id:
                        for i in reversed(range(0, 7)):

                            if product_data[str(i)] >= remaining_quantity:
                                product_data[str(i)] -= remaining_quantity
                                break
                            else:
                                remaining_quantity -= product_data[str(i)]
                                product_data[str(i)] = 0

            all_product_data.append(product_data)

        return all_product_data
