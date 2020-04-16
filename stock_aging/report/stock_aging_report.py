import logging

from odoo import api, fields, models, _
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class ReportStockAging(models.AbstractModel):
    _name = 'report.stock_aging.stock_aging_report'
    _description = 'Stock Aging Report'

    def _get_period_columns(self, data):
        column_data = []
        current_period_lenth = 0
        for i in range(0, 6):
            col = str(current_period_lenth) + "-" + str(current_period_lenth + data['period_length'])
            current_period_lenth += data['period_length']
            column_data.append(col)
        col = "> " + str(current_period_lenth)
        column_data.append(col)
        return column_data

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

    @api.model
    def _get_report_values(self, docids, data):
        return {
            'doc_ids': docids,
            'doc_model': 'stock.quant',
            'data': dict(
                data,
            ),
            'get_period_columns': self._get_period_columns(data['form']),
            'get_product_data_report': self._get_product_data_report(data['form']),

        }