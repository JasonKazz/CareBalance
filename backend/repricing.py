"""Deterministic repricing of an aggregate service basket using Decimal cents."""
import csv
import io
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CODE = re.compile(r'^[A-Z0-9][A-Z0-9_-]{0,23}$')

def valid_code(value):
    if not isinstance(value,str) or not CODE.fullmatch(value.strip().upper()):
        raise ValueError('Service codes must be 1–24 letters, digits, underscores or hyphens.')
    return value.strip().upper()

def amount(value):
    if isinstance(value,bool) or not isinstance(value,(str,int,float,Decimal)):
        raise ValueError('Rates must be nonnegative USD amounts with at most two decimal places.')
    text=str(value).strip().removeprefix('$')
    if ',' in text:
        if not re.fullmatch(r'\d{1,3}(,\d{3})+(\.\d{1,2})?',text): raise ValueError('Invalid currency grouping.')
        text=text.replace(',','')
    if not re.fullmatch(r'\d+(\.\d{1,2})?',text): raise ValueError('Rates must be nonnegative USD amounts with at most two decimal places.')
    try: result=Decimal(text)
    except InvalidOperation: raise ValueError('Invalid rate.')
    if result>1000000: raise ValueError('Rate exceeds the $1,000,000 per-service limit.')
    return result

def parse_activity(text):
    if not isinstance(text,str) or not 1<=len(text)<=500000:
        raise ValueError('Activity CSV must be 1–500,000 characters.')
    reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    required={'code','description','annual_volume','current_rate'}
    if reader.fieldnames is None or set(reader.fieldnames)!=required or len(reader.fieldnames)!=4:
        raise ValueError('CSV headers must be exactly: code,description,annual_volume,current_rate. Use aggregate data only.')
    rows=[]; seen=set()
    try:
        for line in reader:
            if len(rows)>=1000: raise ValueError('Use at most 1,000 service rows.')
            if None in line or any(v is None for v in line.values()): raise ValueError('CSV has missing or extra cells.')
            code=valid_code(line['code'])
            if code in seen: raise ValueError('Duplicate activity code '+code+'. Aggregate into one row per exact code.')
            seen.add(code)
            if not re.fullmatch(r'\d{1,7}',line['annual_volume'].strip()): raise ValueError('Annual volumes must be whole numbers from 0 to 1,000,000.')
            volume=int(line['annual_volume'])
            if volume>1000000: raise ValueError('Annual volume exceeds 1,000,000.')
            rate=amount(line['current_rate'])
            rows.append({'code':code,'description':line['description'][:160], 'annual_volume':volume,
                         'current_rate':float(rate),'csv_row':reader.line_num})
    except csv.Error:
        raise ValueError('Invalid CSV format.') from None
    if not rows or sum(r['annual_volume'] for r in rows)==0: raise ValueError('Include at least one service with positive annual volume.')
    return rows

def reprice(data):
    if not isinstance(data,dict) or data.get('confirmed') is not True:
        raise ValueError('Review and confirm the selected rates before comparison.')
    activity=parse_activity(data.get('activity_csv'))
    rates=data.get('rates')
    if not isinstance(rates,list) or not 1<=len(rates)<=200:
        raise ValueError('Confirm between 1 and 200 proposed rates.')
    uplift=amount(data.get('uplift_pct',0))
    if uplift>30: raise ValueError('Counteroffer uplift must be between 0 and 30 percent.')
    proposed={}
    for row in rates:
        if not isinstance(row,dict): raise ValueError('Invalid rate row.')
        code=valid_code(row.get('code'))
        if code in proposed: raise ValueError('Select only one proposed rate for '+code+'.')
        proposed[code]=(amount(row.get('rate'))*(1+uplift/100)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
    matched=[];unmatched=[]
    current=Decimal(0);future=Decimal(0);all_current=Decimal(0)
    for row in activity:
        old=amount(row['current_rate']);volume=row['annual_volume'];old_total=old*volume;all_current+=old_total
        if row['code'] not in proposed:
            unmatched.append({**row,'current_annual':float(old_total)});continue
        new=proposed[row['code']];new_total=new*volume;current+=old_total;future+=new_total
        matched.append({**row,'proposed_rate':float(new),'current_annual':float(old_total),
            'proposed_annual':float(new_total),'annual_delta':float(new_total-old_total),
            'rate_change_pct':float((new-old)/old*100) if old else None})
    if not matched or sum(r['annual_volume'] for r in matched)==0:
        raise ValueError('No positive-volume exact code matches. Compare your activity codes with the selected contract codes.')
    delta=future-current
    volume=sum(r['annual_volume'] for r in activity);matched_volume=sum(r['annual_volume'] for r in matched)
    return {'matched':matched,'unmatched':unmatched,'unused_contract_codes':sorted(set(proposed)-{r['code'] for r in activity}),
        'summary':{'current_matched':float(current),'proposed_matched':float(future),'annual_delta':float(delta),
            'change_pct':float(delta/current*100) if current else None,'all_current':float(all_current),
            'matched_services':len(matched),'total_services':len(activity),'matched_volume':matched_volume,
            'total_volume':volume,'volume_coverage_pct':matched_volume/volume*100,
            'revenue_coverage_pct':float(current/all_current*100) if all_current else None,
            'uniform_uplift_to_break_even_pct':float(max(Decimal(0),(current/future-1)*100)) if future else None},
        'limitations':['Historical activity is held constant. This is a repricing comparison, not a forecast.',
            'Totals cover matched services only. Unmatched services have unknown proposed reimbursement; they are not valued at zero.',
            'Amounts are modeled fee-schedule reimbursement, not profit or cash collections. Costs, denials, payer/patient responsibility, timing, and clinical outcomes are not modeled.',
            'Selected rates are user-confirmed inputs. Code matching is exact, including any supplied modifier; no coding or contract applicability is inferred.']}
