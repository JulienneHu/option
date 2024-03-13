from flask import Flask, request, render_template_string
import yfinance as yf
from datetime import datetime
import holidays
import pytz

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        company = request.form.get("company")
        date = request.form.get("date")
        strike = float(request.form.get("strike"))
        output = main(company, date, strike)
        return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Option Price Fetcher</title>
            </head>
            <body>
                <h1>Option Price Results</h1>
                <pre>{{output}}</pre>
                <a href="/">Try another</a>
            </body>
            </html>
        """, output=output)
    else:
        # Initial page load, show the form
        return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Option Price Fetcher</title>
            </head>
            <body>
                <h1>Enter Option Details</h1>
                <form method="post">
                    Company Symbol: <input type="text" name="company" > <span>example: AAPL</span><br>
                    Date (YYYY-MM-DD): <input type="text" name="date" > <span>format: YYYY-MM_DD<span><br>
                    Strike Price: <input type="number" name="strike"> <span>example: 100<span><br>
                    <input type="submit" value="Submit">
                </form>
            </body>
            </html>
        """)

def get_realtime_option_price(option_name):
    '''
    This function gets the real-time option price in the US stock market.
    It considers the market closed during weekends, US public holidays, and off-hours.
    '''
    # Process input option name
    today = datetime.today()
    company = option_name[:next((i for i, char in enumerate(option_name) if char.isdigit()), None)]
    comp_info = yf.Ticker(company)
    
    length = len(company)
    date = option_name[length:length + 6]
    option_date = f"20{date[:2]}-{date[2:4]}-{date[4:]}"
    
    optionType = option_name[length + 6]
    opt = comp_info.option_chain(option_date)  

    if optionType.upper() == "C":
        specific_opt = opt.calls[opt.calls.contractSymbol == option_name] 
    else:
        specific_opt = opt.puts[opt.puts.contractSymbol == option_name]

    output = ''
    if specific_opt.empty:
        output += f"No specific option found for {option_name}."
        return output

    # Check if today is a weekend or holiday
    if today.weekday() > 4 or today in holidays.UnitedStates(years=today.year):
        market_status = "weekend" if today.weekday() > 4 else "a holiday"
        last_price = specific_opt["lastPrice"].iloc[0] if not specific_opt.empty else "N/A"
        output += f"Today is {market_status}, the market is closed. The last recorded transaction price of {option_name} was {last_price}.\n"
    else:
        # Define the market hours
        market_open = datetime.strptime("09:30", "%H:%M").time()
        market_close = datetime.strptime("16:00", "%H:%M").time()

        # Check if current time is within market hours
        eastern = pytz.timezone('US/Eastern')
        current_time_et = datetime.now(eastern).time()

        if market_open <= current_time_et <= market_close:
            last_price = specific_opt["lastPrice"].iloc[0]
            ask_price = specific_opt["ask"].iloc[0]
            bid_price = specific_opt["bid"].iloc[0]
            output += f"Market is open. Last price: {last_price}, Ask: {ask_price}, Bid: {bid_price}.\n"
        else:
            last_price = specific_opt["lastPrice"].iloc[0]
            output +=f"Market is closed. The last recorded transaction price of {option_name} was {last_price}.\n"
    
    return last_price, output

def calls_or_puts(company, date, strike):
    output = ""
    option_names = []  # List to hold the exact option names
    ticker = yf.Ticker(company)
    expiration_dates = ticker.options

    if date in expiration_dates:
        opts = ticker.option_chain(date)
        call_option = opts.calls[opts.calls['strike'] == strike]
        put_option = opts.puts[opts.puts['strike'] == strike]

        if not call_option.empty:
            call_option_names = call_option['contractSymbol'].tolist()
            call = ', '.join(call_option_names)
            option_names.extend(call_option_names)  # Add call option names to the list
            output += f"Call option for strike price {strike} on {date}: {call}\n"
        else:
            output += f"No call option with a strike price of {strike} for {date}.\n"

        if not put_option.empty:
            put_option_names = put_option['contractSymbol'].tolist()
            put = ', '.join(put_option_names)
            option_names.extend(put_option_names)  # Add put option names to the list
            output += f"Put option for strike price {strike} on {date}: {put}\n"
        else:
            output += f"No put option with a strike price of {strike} for {date}.\n"
    else:
        output += f"No options available for {date}.\n"

    return option_names, output

def main(company='AAPL', date='2024-03-15', strike=100):
    result = ""
    options, options_output = calls_or_puts(company, date, strike)
    result += options_output  
    result += '\n'
    if options:
        for option in options:
            _, option_info = get_realtime_option_price(option)  # Unpack the tuple
            result += option_info   
            result += '\n'  

    return result


