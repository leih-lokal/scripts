import leihlokal




if __name__=='__main__':
    store = leihlokal.LeihLokal()
    active_rentals = store.get_active_rentals()
    active_rentals = [x for x in active_rentals if '2020' in str(x.rented_on)]
    customers = [x.customer for x in active_rentals]

