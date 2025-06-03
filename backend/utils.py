def month_name_genitive(date):
    """Возвращает название месяца в родительном падеже"""
    print(date)
    try:
        if isinstance(date, int) and date > 0 and date < 13:
            print("Integer")
            month_mapping = {
            1: 'Января',
            2: 'Февраля',
            3: 'Марта',
            4: 'Апреля',
            5: 'Мая',
            6: 'Июня',
            7: 'Июля',
            8: 'Августа',
            9: 'Сентября',
            10: 'Октября',
            11: 'Ноября',
            12: 'Декабря'}
            return month_mapping.get(date)
        else:
            print("Datetime")
            month_mapping = {
            'Январь': 'Января',
            'Февраль': 'Февраля',
            'Март': 'Марта',
            'Апрель': 'Апреля',
            'Май': 'Мая',
            'Июнь': 'Июня',
            'Июль': 'Июля',
            'Август': 'Августа',
            'Сентябрь': 'Сентября',
            'Октябрь': 'Октября',
            'Ноябрь': 'Ноября',
            'Декабрь': 'Декабря'}   
            nominative = date.month_name(locale="Russian")
            return month_mapping.get(nominative, nominative)
    except TypeError:
        print("Invalid date format. Please provide a valid date.")
        return None
    
def month_name(date):
    """Возвращает название месяца в родительном падеже"""
    print(date)
    try:
        if isinstance(date, int) and date > 0 and date < 13:
            print("Integer")
            month_mapping = {
            1: 'Январь',
            2: 'Февраль',
            3: 'Март',
            4: 'Апрель',
            5: 'Май',
            6: 'Июнь',
            7: 'Июль',
            8: 'Август',
            9: 'Сентябрь',
            10: 'Октябрь',
            11: 'Ноябрь',
            12: 'Декабрь'}
            return month_mapping.get(date)
        else:
            print("Datetime")
            month_mapping = {
            'Январь': 'Январь',
            'Февраль': 'Февраль',
            'Март': 'Март',
            'Апрель': 'Апрель',
            'Май': 'Май',
            'Июнь': 'Июнь',
            'Июль': 'Июль',
            'Август': 'Август',
            'Сентябрь': 'Сентябрь',
            'Октябрь': 'Октябрь',
            'Ноябрь': 'Ноябрь',
            'Декабрь': 'Декабрь'}   
            nominative = date.month_name(locale="Russian")
            return month_mapping.get(nominative, nominative)
    except TypeError:
        print("Invalid date format. Please provide a valid date.")
        return None