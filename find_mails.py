import leihlokal




if __name__=='__main__':
    store = leihlokal.LeihLokal()
    active_rentals = store.get_active_rentals()
    active_rentals = [x for x in active_rentals if '2021' in str(x.rented_on)]
    customers = list(set([x.customer for x in active_rentals]))

    no_phone = [x for x in customers if x.email=='' or 'cyn' in x.email or 'gal' in x.email]
