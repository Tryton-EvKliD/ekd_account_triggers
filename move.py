# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2009-today Dmitry klimanov
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
#
##############################################################################
'MoveRU'
from trytond.model import ModelView, ModelSQL, fields
from decimal import Decimal
import datetime
from trytond.modules.ekd_account.account import _PARTY, _PRODUCT, _MONEY
import profile

class MoveRU(ModelSQL, ModelView):
    _name = "ekd.account.move"

#    def button_post(self, ids):
#        return self.post_entries(ids)

#    def button_cancel(self, ids):
#        return self.post_cancel(ids)

#    def button_deleted(self, ids):

#    def create(self, vals):

#    def write(self, ids, vals):

    def delete(self, ids):
        if isinstance(ids, (int, long)):
            ids = [ids]
        for move in self.browse(ids):
            if move.state == 'posted':
                self.raise_user_warning(
                            '%s@account_ru_move' % move.id,
                            'delete_posted_move')
            for line in move.lines:
                if line.state in ('draft', 'canceled', 'deleted'):
                    line.delete(line.id)
                elif line.state == 'posted':
                    self.raise_user_warning(
                            '%s@account_ru_move_line' % line.id,
                            'delete_posted_line')
                    line.post_in_cancel([line.id])
                    line.delete([line.id])
                else:
                    line.delete([line.id])
        return super(MoveRU, self).delete(ids)

    def post_cancel(self, ids):
        line_ru_obj = self.pool.get('ekd.account.move.line')

        pool_obj = {
                'account': self.pool.get('ekd.balances.account'),
                'analytic': self.pool.get('ekd.balances.analytic'),
                'party': self.pool.get('ekd.balances.party'),
                'fixed_assets': self.pool.get('ekd.balances.fixed_assets'),
                'intangible_assets': self.pool.get('ekd.balances.intangible_assets'),
                'material': self.pool.get('ekd.balances.material'),
                'goods': self.pool.get('ekd.balances.goods'),
                'finance': self.pool.get('ekd.balances.finance'),
                'period': self.pool.get('ekd.period')
                }

        if isinstance(ids, (int, long)):
            ids = [ids]
        for move in self.browse(ids):
            if not move.period:
                self.raise_user_error('period_not_find')
            elif not move.period_open:
                self.raise_user_error('period_is_closed')

            if line_ru_obj.post_cancel(move.lines, pool_obj, period=move.period):
                self.write(move.id, {
                            'state': 'canceled',
                            'post_date': None,
                            })
            else:
                self.raise_user_error('Unknown Error!')


    def post(self, ids):
        bal_account_obj = self.pool.get('ekd.balances.account')
        period_obj = self.pool.get('ekd.period')
        line_ru_obj = self.pool.get('ekd.account.move.line')
        sequence_obj = self.pool.get('ir.sequence')
        date_obj = self.pool.get('ir.date')
        line_post = line_ru_obj.post_line

        if isinstance(ids, (int, long)):
            ids = [ids]
        pool_obj = {
                'account': self.pool.get('ekd.balances.account'),
                'analytic': self.pool.get('ekd.balances.analytic'),
                'party': self.pool.get('ekd.balances.party'),
                'fixed_assets': self.pool.get('ekd.balances.fixed_assets'),
                'intangible_assets': self.pool.get('ekd.balances.intangible_assets'),
                'material': self.pool.get('ekd.balances.material'),
                'goods': self.pool.get('ekd.balances.goods'),
                'finance': self.pool.get('ekd.balances.finance'),
                'period': self.pool.get('ekd.period')
                }

        for move in self.browse(ids):
            if not move.period:
                self.raise_user_error('period_not_find')
            elif not move.period_open:
                self.raise_user_error('period_is_closed')

            if move.period:
                period = move.period
            elif move.date_operation:
                period_id = period_obj.find(line.company, date=move.date_operation)
                period = self.pool.get('ekd.period').browse(period_id)
            else:
                self.raise_user_error("Date operation don't find!")

            if line_post(move.lines, pool_obj, period=period):
                pass
            else:
                self.raise_user_error('Unknown Error!')

        #raise Exception('POSt LINE', line.state)
        super(MoveRU, self).post(ids)
        return True

MoveRU()

class LineRU(ModelSQL, ModelView):
    _name="ekd.account.move.line"

    def button_post(self, ids):
        return self.post(ids)

    def button_cancel(self, ids):
        return self.post_in_cancel(ids)

    def post(self, ids):
        super(LineRU, self).post(ids)
        return self.post_in_line(ids)

    def post_in_line(self, ids):
        return self.post_line(self.browse(ids))

    def post_in_cancel(self, ids):
        return self.post_cancel(self.browse(ids))

    def analytic_level_post(self, line, analytic_post_balance=None, analytic=[], product={}, period=None, debit=True):
        if debit:
            return analytic_post_balance({
                    'period': period,
                    'fiscalyear': period.fiscalyear,
                    'date_operation':line.date_operation,
                    'account': line.dt_account,
                    'account_kind': line.dt_kind,
                    'account_type': line.dt_kind_analytic,
                    'month': line.date_operation.strftime('%m'),
                    'uom': line.product_uom.id,
                    'unit_price': line.unit_price,
                    'analytic': analytic,
                    'product': product,
                    'debit': line.amount,
                    'qdebit': line.quantity,
                    })
        else:
            return analytic_post_balance({
                    'period': period,
                    'fiscalyear': period.fiscalyear,
                    'date_operation':line.date_operation,
                    'account': line.ct_account,
                    'account_kind': line.ct_kind,
                    'account_type': line.ct_kind_analytic,
                    'uom': line.product_uom.id,
                    'unit_price': line.unit_price,
                    'month': line.date_operation.strftime('%m'),
                    'analytic': analytic,
                    'product': product,
                    'credit': line.amount,
                    'qcredit': line.quantity,
                    })

    def analytic_level_cancel(self, line, analytic_post_cancel=None, analytic=[], product={}, period=None, debit=True):
        if debit:
            return analytic_post_cancel({
                    'period': period,
                    'fiscalyear': period.fiscalyear,
                    'date_operation':line.date_operation,
                    'account': line.dt_account,
                    'account_kind': line.dt_kind,
                    'account_type': line.dt_kind_analytic,
                    'month': line.date_operation.strftime('%m'),
                    'uom': line.product_uom.id,
                    'unit_price': line.unit_price,
                    'analytic': analytic,
                    'product': product,
                    'debit': line.amount,
                    'qdebit': line.quantity,
                    })
        else:
            return analytic_post_cancel({
                    'period': period,
                    'fiscalyear': period.fiscalyear,
                    'date_operation':line.date_operation,
                    'account': line.ct_account,
                    'account_kind': line.ct_kind,
                    'account_type': line.ct_kind_analytic,
                    'month': line.date_operation.strftime('%m'),
                    'uom': line.product_uom.id,
                    'unit_price': line.unit_price,
                    'analytic': analytic,
                    'product': product,
                    'credit': line.amount,
                    'qcredit': line.quantity,
                    })

    def account_money_post(self, line, money_post_balance=None, period=None, debit=True):
        if debit:
            return money_post_balance({
                            'company':line.company,
                            'period':period,
                            'date_operation':line.date_operation,
                            'account':line.dt_account,
                            'debit': line.amount,
                            })
        else:
            return money_post_balance({
                    'company':line.company,
                    'period':period,
                    'date_operation':line.date_operation,
                    'account':line.ct_account,
                    'credit': line.amount,
                    })

    # Обработка в учете строк
    #sorted_keys = sorted(level_parent.items(),key=lambda x:x[0])
    def post_line(self, lines_obj, balance_obj=None, period=None):
        if balance_obj is None:
            balance_obj = {
                'account': self.pool.get('ekd.balances.account'),
                'analytic': self.pool.get('ekd.balances.analytic'),
                'party': self.pool.get('ekd.balances.party'),
                'fixed_assets': self.pool.get('ekd.balances.fixed_assets'),
                'intangible_assets': self.pool.get('ekd.balances.intangible_assets'),
                'material': self.pool.get('ekd.balances.material'),
                'goods': self.pool.get('ekd.balances.goods'),
                'finance': self.pool.get('ekd.balances.finance'),
                'period': self.pool.get('ekd.period'),
                }
        analytic_post_balance = {
                'party': balance_obj.get('party').post_balance,
                'analytic': balance_obj.get('analytic').post_balance,
                'fixed_assets': balance_obj.get('fixed_assets').post_balance,
                'goods': balance_obj.get('goods').post_balance,
                'finance': balance_obj.get('finance').post_balance,
                }
        line_analytic_dt_write = self.pool.get('ekd.account.move.line.analytic_dt').write
        line_analytic_ct_write = self.pool.get('ekd.account.move.line.analytic_ct').write
        account_post_balance = balance_obj.get('account').post_balance

        for line in lines_obj:
            if line.state in ('posted', 'deleted'):
                continue
            if not line.date_operation:
                line.write(line.id, {'date_operation': line.move.date_operation},)
            if not period:
                period_id = balance_obj['period'].find(line.company, date=line.date_operation)
                period = balance_obj['period'].browse(period_id)

            if not line.move.period_open:
                self.raise_user_error('Period is close!')
            dt_balance=0
            ct_balance=0
            dt_balance2=0
            ct_balance2=0

            # Проверка на расширенный тип аналитики счета
            if line.dt_analytic_level:
                analytic = []
                product = {}
                if line.dt_kind_analytic in _PRODUCT:
                    product['product'] = line.product
                    product['uom'] = line.product_uom
                    product['unit_price'] = line.unit_price

                for analytic_line in line.dt_analytic_accounts:
                    analytic.append({
                        'id': analytic_line.id, 
                        'level': analytic_line.level,
                        'model_ref': analytic_line.analytic,
                        })

                if line.dt_kind_analytic in _PARTY:
                    dt_balance2 = self.analytic_level_post(line, 
                            analytic_post_balance['party'], 
                            analytic, period=period, debit=True)
                elif line.dt_kind_analytic in _MONEY:
                    dt_balance2 = self.analytic_level_post(line, 
                            analytic_post_balance['finance'], 
                            analytic, period=period, debit=True)
                else:
                    dt_balance2 = self.analytic_level_post(line, 
                            analytic_post_balance[line.dt_kind_analytic], 
                            analytic, product, period=period, debit=True)
                #raise Exception(str(dt_balance2))

                if isinstance(dt_balance2, dict):
                    for analytic_ids in dt_balance2.keys():
                        line_analytic_dt_write(analytic_ids, {
                            'ref_analytic':dt_balance2[analytic_ids][0],
                            'ref_period':dt_balance2[analytic_ids][1]})
                    dt_balance2 = 0

            if line.dt_kind_analytic in _MONEY:
                    dt_balance2 = self.account_money_post(line, 
                            analytic_post_balance['finance'],
                            period, debit=True)

            if line.ct_analytic_level:
                analytic = []
                product = {}
                if line.ct_kind_analytic in _PRODUCT:
                    product['product'] = line.product
                    product['uom'] = line.product_uom
                    product['unit_price'] = line.unit_price

                for analytic_line in line.ct_analytic_accounts:
                    analytic.append({
                        'id': analytic_line.id, 
                        'level': analytic_line.level,
                        'model_ref': analytic_line.analytic,
                        'product':product,
                        })

                if line.ct_kind_analytic in _PARTY:
                    ct_balance2 = self.analytic_level_post(line, 
                        analytic_post_balance['party'], 
                        analytic, period=period, debit=False)
                elif line.ct_kind_analytic in _MONEY:
                    ct_balance2 = self.analytic_level_post(line, 
                        analytic_post_balance['finance'], 
                        analytic, period=period, debit=False)
                else:
                    ct_balance2 = self.analytic_level_post(line, 
                        analytic_post_balance[line.ct_kind_analytic], 
                        analytic, product, period=period, debit=False)

                if isinstance(ct_balance2, dict):
                    for analytic_ids in ct_balance2.keys():
                        line_analytic_ct_write(analytic_ids, {
                            'ref_analytic':ct_balance2[analytic_ids][0],
                            'ref_period':ct_balance2[analytic_ids][1]})
                    ct_balance2 = 0

            if line.ct_kind_analytic in _MONEY:
                    ct_balance2 = self.account_money_post(line, 
                            analytic_post_balance['finance'],
                            period, debit=False)

            if line.dt_account:
                dt_balance = account_post_balance({
                    'company':line.company.id,
                    'period':period,
                    'date_operation':line.date_operation,
                    'account':line.dt_account.id,
                    'account_kind':line.dt_kind,
                    'debit': line.amount,
                    })

            if line.ct_account:
                ct_balance = account_post_balance({
                    'company':line.company.id,
                    'period':period,
                    'date_operation':line.date_operation,
                    'account':line.ct_account.id,
                    'account_kind':line.dt_kind,
                    'credit': line.amount,
                    })

            self.write(line.id, {
                    #'post_date': datetime.datetime.now().strftime('%Y-%m-%d'),
                    #'state': 'posted',
                    'dt_balance':dt_balance,
                    'ct_balance':ct_balance,
                    'dt_balance2':dt_balance2,
                    'ct_balance2':ct_balance2
                    })

        return True

    def account_money_cancel(self, line, money_cancel_balance=None, period=None, debit=True):
        if debit:
            return money_cancel_balance({
                            'company':line.company,
                            'period':period,
                            'date_operation':line.date_operation,
                            'account':line.dt_account,
                            'debit': line.amount,
                            'balance_id': line.dt_balance2,
                            })
        else:
            return money_cancel_balance({
                    'company':line.company,
                    'period':period,
                    'date_operation':line.date_operation,
                    'account':line.ct_account,
                    'credit': line.amount,
                    'balance_id': line.ct_balance2,
                    })

    def post_cancel(self, lines_obj, balance_obj=None, period=None):
        if balance_obj is None:
            balance_obj = {
                'account': self.pool.get('ekd.balances.account'),
                'analytic': self.pool.get('ekd.balances.analytic'),
                'party': self.pool.get('ekd.balances.party'),
                'fixed_assets': self.pool.get('ekd.balances.fixed_assets'),
                'intangible_assets': self.pool.get('ekd.balances.intangible_assets'),
                'material': self.pool.get('ekd.balances.material'),
                'goods': self.pool.get('ekd.balances.goods'),
                'finance': self.pool.get('ekd.balances.finance'),
                'period': self.pool.get('ekd.period')
                }
        analytic_post_cancel = {
                'party': balance_obj.get('party').post_cancel,
                'analytic': balance_obj.get('analytic').post_cancel,
                'goods': balance_obj.get('goods').post_cancel,
                'finance': balance_obj.get('finance').post_cancel,
                }
        line_analytic_dt_write = self.pool.get('ekd.account.move.line.analytic_dt').write
        line_analytic_ct_write = self.pool.get('ekd.account.move.line.analytic_ct').write
        line_for_erase=[]
        erase_values={
                'ref_analytic': None,
                'ref_period': None,
                    }
        for line in lines_obj:
            if line.state in ('draft', 'canceled', 'deleted'):
                continue

            if period is None:
                period_id = balance_obj.get('period').find(line.company, line.date_operation)
                period = balance_obj.get('period').browse(period_id)

            if period.state == 'close':
                self.raise_user_error('period_is_closed')
            # Проверка типа аналитики счета
            if line.dt_analytic_level:
                analytic = []
                product = {}
                if line.dt_kind_analytic in _PRODUCT:
                    product['product'] = line.product
                    product['uom'] = line.product_uom
                    product['unit_price'] = line.unit_price

                for analytic_line in line.dt_analytic_accounts:
                    analytic.append(analytic_line)

                if line.dt_kind_analytic in _PARTY:
                    dt_balance2 = self.analytic_level_cancel(line, 
                            analytic_post_cancel.get('party'), 
                            analytic, period=period, debit=True)
                elif line.dt_kind_analytic in _MONEY:
                    dt_balance2 = self.analytic_level_cancel(line, 
                            analytic_post_cancel.get('finance'), 
                            analytic, period=period, debit=True)
                else:
                    dt_balance2 = self.analytic_level_cancel(line, 
                            analytic_post_cancel.get(line.dt_kind_analytic), 
                            analytic, product, period=period, debit=True)

                line_analytic_dt_write(
                            [ x.id for x in line.dt_analytic_accounts ],
                            erase_values)
                dt_balance2 = 0

            if line.dt_kind_analytic in _MONEY:
                dt_balance2 = self.account_money_cancel(line, 
                            analytic_post_cancel['finance'],
                            period, debit=True)

            if line.ct_analytic_level:
                analytic = []
                product = {}
                if line.ct_kind_analytic in _PRODUCT:
                    product['product'] = line.product
                    product['uom'] = line.product_uom
                    product['unit_price'] = line.unit_price

                for analytic_line in line.ct_analytic_accounts:
                    analytic.append(analytic_line)

                if line.ct_kind_analytic in _PARTY:
                    ct_balance2 = self.analytic_level_cancel(line, 
                            analytic_post_cancel.get('party'), 
                            analytic, period=period, debit=False)
                elif line.ct_kind_analytic in _MONEY:
                    ct_balance2 = self.analytic_level_cancel(line, 
                            analytic_post_cancel.get('finance'), 
                            analytic, period=period, debit=False)
                else:
                    ct_balance2 = self.analytic_level_cancel(line, 
                            analytic_post_cancel.get(line.ct_kind_analytic), 
                            analytic, product, period=period, debit=False)

                line_analytic_ct_write(
                            [ x.id for x in line.ct_analytic_accounts ],
                            erase_values)
                ct_balance2 = 0

            if line.ct_kind_analytic in _MONEY:
                    ct_balance2 = self.account_money_cancel(line, 
                            analytic_post_cancel['finance'],
                            period, debit=False)

            if line.dt_account:
                dt_balance = balance_obj.get('account').post_cancel({
                            'company':line.move.company,
                            'period':period,
                            'account':line.dt_account,
                            'debit': line.amount,
                            'balance_id': line.dt_balance,
                            })

            if line.ct_account:
                ct_balance = balance_obj.get('account').post_cancel({
                            'company':line.move.company,
                            'period':period,
                            'account':line.ct_account,
                            'credit': line.amount,
                            'balance_id': line.ct_balance,
                            })
            line_for_erase.append(line.id)

        self.write(line_for_erase, {
                            'post_date': None,
                            'dt_balance': None,
                            'ct_balance': None,
                            'dt_balance2': None,
                            'ct_balance2': None
                            })
        super(LineRU, self).post_cancel(line_for_erase)
        return True

LineRU()
