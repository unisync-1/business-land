# -*- coding: utf-8 -*-

import logging
from odoo import models, fields
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):

    _inherit = "res.partner"

    credit_limit_days = fields.Integer(string="Credit Limit(Days)")
    credit_limit_amount = fields.Float(string="Credit Limit Amount")
