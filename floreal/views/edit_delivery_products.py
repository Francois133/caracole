#!/usr/bin/python3
# -*- coding: utf8 -*-

"""Helpers to edit products list: generate suggestions based on current and
past products, parse POSTed forms to update a delivery's products list."""

import django
from django.shortcuts import render, redirect
if django.VERSION < (1, 8):
    from django.core.context_processors import csrf
else:
    from django.template.context_processors import csrf
from django.http import HttpResponseForbidden

from .getters import get_delivery
from .decorators import nw_admin_required
from ..models import Product, Delivery, JournalEntry
from ..forms import DeliveryForm, ProductFormSet, ProductsSet, ProductForm
from ..penury import set_limit


@nw_admin_required(lambda a: get_delivery(a['delivery']).network)
def edit_delivery_products(request, delivery):
    """Edit a delivery (name, state, products). Network staff only."""
#TO DO some error processing, messaging the user
    delivery = get_delivery(delivery)

    if request.user not in delivery.network.staff.all():
        return HttpResponseForbidden('Réservé aux administrateurs du réseau '+delivery.network.name)

    if request.method == 'POST':  # Handle submitted data
        JournalEntry.log(request.user, "Edited products for delivery %s/%s", delivery.network.name, delivery.name)
        d=request.POST
        print(d)
        parse_and_save(d, delivery)
        if 'SauvRet' in d:
            return redirect('edit_delivery', delivery.id)
        else: #reload the page
            return redirect('edit_delivery_products', delivery.id)
    else:  # Create and populate forms to render
        return prepare_and_render(request,delivery)
        
        
def prepare_and_render(request,delivery):
    deliv = DeliveryForm(instance=delivery,prefix = 'dv', auto_id = '%s') 
    # prefix est pour le champ name, auto_id dérive du nom ici dv-description    
    # auto_id = 'dv-%s" ne marche que pour le champ id
    formset= [] # on devrait utiliser formset_factory, ou modelformset_factory avec initial, 
# il y a queryset comme paramètre, à regarder quand même. la flemme
    for ind, product in enumerate(delivery.product_set.all(), start=1) : # order place
        my_prefix = 'r'+str(ind)
        #rearrange places
        if product.place != ind :
            product.place = ind
            product.save()
        my_product_form = ProductForm(instance = product, prefix = my_prefix)
        my_product_form.update_described() # widget update for showing or not description
        formset.append(my_product_form)
    siz=len(formset) # Add 3 blank lines
    for i in range(siz+1,siz+4):
        my_product = Product(place=i)
        prodform = ProductForm(instance = my_product, prefix ='r'+str(i))
        prodform.fields['name'].required = False
        prodform.fields['price'].required = False
        formset.append(prodform)
            # auto_id à False pour l'id des inputs et des textareas ? pour la textarea '%s-' soit r1-
# y a de l'idée   
# TO DO works because we order by place, this shall be the product id to save it, but the logics of the template
# would have to also change, in auto_id '%s-' would mean id will be prefixed by r1-, 
# prefix is for the names of the fields                
        
    vars = {'QUOTAS_ENABLED': False,
                'user': request.user,
                'delivery': delivery,
                'deliv_form' : deliv,
                'prodformset': formset,
                }
    vars.update(csrf(request))
    return render(request,'edit_delivery_products.html', vars)


def parse_and_save(request_post,deliv):
    """Rebuild forms, validate them to transform strings fields into model fields, save data
    the data parameter of a forms is made for that and is thought as a string dictionnary 
    for this reverse transformation : 
    it is stated NOWHERE IN THE MOTHER OF FNUCNING GOD DOCUMENTATION 
    use ProductForm(data, instance=product), product.initial is then what we need...
    """
    data_del = get_delivery_from_data(request_post,'dv')
    deliv_form = DeliveryForm(data_del,instance=deliv) 
    # ET qu'est-ce qu'on obtient, un $&!# de formulaire lié !!! (si)
    if deliv_form.is_valid() : #populate cleaned_data as fields linked with model (!) 
        if  (deliv_form.has_changed()):
            print("Description saved", deliv)
            deliv_form.save()
    n_rows = int(request_post['n_rows'])

    for i in range(1,n_rows):
        pref = 'r'+str(i)
        data_prod = get_product_from_data(request_post,pref)
        try : 
            if  not (data_prod['id'] == 'None' or data_prod['id'] == ''): #None for blank products
                product = Product.objects.get(pk=int(data_prod['id']))
                if 'deleted' in data_prod :
                    product.delete()
                else : 
                    prod_form = ProductForm(data_prod, instance= product)
                    if prod_form.is_valid():
                        if prod_form.has_changed():
                            print("Updating produit ", pref, prod_form.changed_data)
                            prod_form.save()
            else : # blank product
                if 'deleted' not in data_prod :
                    if data_prod['name'] != '' and data_prod['price'] != '':
                        prod_form= ProductForm(data_prod)
                        if prod_form.is_valid():
                            data = prod_form.cleaned_data
                            del data['described']
                            del data['deleted']
                            data['delivery']=deliv
                            if data['unit'] == None:
                                data['unit'] = 'pièce'
                                data['unit_weight'] = 0
                            if data['quantum'] == None :
                                data['quantum'] = 1
                            prodi = Product.objects.create(**data)
                            prodi.save() #for automatic id
                            #print(prodi, " créé")
               
        except Exception as exc:
            print("Form Validation error ", exc, pref )
            print(data)
    

def get_delivery_from_data(req,prefix):
    """req is a QueryDict, prefix is dv-, called with prefix='dv'"""
    data = {}
    fields=['name','state','description']
    for champ in fields:
        data[champ]=req.get(prefix+'-'+champ)
    return data

def get_product_from_data(req, prefix):
    """ get data for fields with an id
    req is a QueryDict, prefix is rx-, called with prefix='rx'
    return {'id' : id, 'deleted' : True } if rx-deleted is found """
    data = {}
    fields = ['name', 'price', 'quantity_per_package', 'unit', 'quantity_limit', 'quantum', 'unit_weight',
              'place', 'description', 'described']
    pref = prefix + '-' 
    ident = req.get(prefix+'-'+'id','') 
    data['id'] = ident   
    if prefix+'-'+'deleted' in req :
        data['deleted']= True
    else :
        for champ in fields:
            data[champ]=req.get(prefix+'-'+champ) 
        if data['described']==None : #described hidden not transmitted
            data['description'] = ''
        del data['described']
    return data


    # In case of change in quantity limitations, adjust granted quantities for purchases
    #for pd in dv.product_set.all():
    #    set_limit(pd)
