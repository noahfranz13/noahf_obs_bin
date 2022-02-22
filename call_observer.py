#!/usr/bin/env python
# S. Croft 2020/09/11

from twilio.rest import Client
import pandas as pd
import os

account_sid = os.environ['TWILIO_ACCOUNT']
auth_token = os.environ['TWILIO_AUTH']

def get_current_observer():
    url = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRG_GlslAbagkXZcQTRxijAv19ntEshsrHG3XbakhHzzcej6aHpZ7PBcw5MO_jVB3awrBLR-uTFb0xR/pub?gid=547397209&single=true&output=csv'

    current = pd.read_csv(url).tail(1)

    cells = {'Steve'  : '+19253210871', \
        'Julia'  : '+12409971036', \
        'Bryan'  : '+15623097635', \
        'Office' : '+15106425555', \
        'Sofia'  : '+18649407093', \
        'Vishal' : '+15108132274', \
        'Matt'   : '+15102070832', \
        'Dave'   : '+19252161532', \
        'Danny'  : '+61423211715', \
        'Howard' : '+14158460436'}

    name = current['Primary'].iloc[0]

    if name == 'Custom':
        cell = current['PrimaryCell'].iloc[0]
    else:
        cell = cells[name]

    return(name,cell)

def make_call(message, number):
    client = Client(account_sid, auth_token)
    call = client.calls.create(
                        twiml='<Response><Say voice="Polly.Joanna">'+message+'</Say></Response>',
                        to=number,
                        from_='+13042416788'
                    )
    #print(call.status)

def call_observer(submessage):
    (observer, number_to_call) = get_current_observer()
    message = "Hello "+observer+". "+submessage
    print "Calling",observer,"at",number_to_call,"with message '"+message+"'"
    make_call(message, number_to_call)

if __name__ == '__main__':    
    import argparse

    parser = argparse.ArgumentParser(description="Call the observer")
    parser.add_argument('-m',default="The GBT has experienced a fault. Please check your VNC.",help="Message")
    parser.add_argument('-n',help="Number to call (defaults to current primary observer) [+][country code][phone number including area code]")
    args = parser.parse_args()
        
    if args.n:
        number_to_call = args.n
        observer = "GBT observer"
    else:
        (observer,number_to_call) = get_current_observer()
    message = "Hello "+observer+". "+args.m
    make_call(message, number_to_call)

    

