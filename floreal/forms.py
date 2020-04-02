#!/usr/bin/python3
# -*- coding: utf-8 -*-

from django import forms
from .models import Delivery, Product
from django_summernote.widgets import SummernoteWidget, SummernoteInplaceWidget
from django.forms.widgets import Textarea
from django.forms import modelformset_factory, formset_factory

class ProductForm(forms.ModelForm):
    """Sous forme d'une table, on a besoin d'initier les donnees, il faut recuperer l'id
    d'un produit et rajouter les flêches pour le swap
    on affiche un produit sur une ligne dans un <table> 
    On a une foreign key vers Delivery dans le modèle
    Rappel : manytomany fields are processed by a ModelMultipleChoiceField
    ForeignKey par un ChoiceField, ce qu'on ne veut pas"""
    #def __init__(self,*args, **kwargs) :
    #    super().__init__(self,*args,**kwargs) 
    #    self.auto_id=False
        
    described = forms.BooleanField(required=False) # Faut-il rajouter une description au produit ou effacer le champ description
    deleted = forms.BooleanField(required=False) # Faut-il effacer le produit après la requête, plutôt utiliser can_delete de django   


    class Meta:
        model = Product # recupère tous les champs
        exclude = ('delivery',) #par défaut un choix de delivery
        widgets = { 'description' : Textarea(attrs={'rows':'5'}),
                }
#       widgets = {
#               'description' : SummernoteWidget(attrs={'summernote' : {'width':'98%', 'height':'130px', 'airMode':False, 'iframe':False ,
#'toolbar' : ['bold','italic', ['fontname', ['fontname']],['fontsize', ['fontsize']],['color', ['color']],'picture','codeview'],
#       }}),
#       }
    # we can do airMode on the edit_product because we have already the js from the delivery description ?

ProductFormSet= modelformset_factory(Product,exclude=('delivery',),extra=2) 

ProductsSet = formset_factory(ProductForm, extra=3) # On peut faire un set mais pas de modèle, on n'a pas de save

class DeliveryForm(forms.ModelForm):
    """Le formulaire pour editer une livraison, template edit_delivery_products
    Utilisation possible de ce qui s'appelle dans la doc formulaires groupés
    C'est l'ensembe deux formulaires : un de Delivery et un ensemble de ProductForm
    On intialise un objet de type Form avec request.POST et on passe comme argument
    au template 'form' : form avec form de type Form 
    Idéalement il faut afficher <tr> <div> ...tous les fields sauf descriptions </div> </tr>
    puis <tr> la textarea si description est non nulle </tr>
   """ 
    #auto_id='dv-%s' #ne marche pas en attribut de classe, ne marche qu'à la construction de l'objet ?

    class Meta:
        model = Delivery
        exclude = ('datedelivery','network')
        widgets = { 
            'description' : SummernoteWidget(attrs={
                   #'id' : 'dv-description',    
                   'summernote' : {'width':'100%', 'height':'300px', 'airMode':False, 'theme': 'light', 'iframe':False },
                    }),
        }
        # l'autre syntaxe est fields pour spécifier les fields


