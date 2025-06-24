from flask import Flask, render_template, request
import sqlite3 as sql
import datetime as T

app = Flask(__name__)
Db = 'ibn_aqlan_building.db'

def init_db():
    Con = sql.connect(Db)
    cur = Con.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS apartments(
        id INTEGER PRIMARY KEY,
        apartment_id INTEGER,
        tenant_name TEXT,
        meter_number TEXT)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS meter_readings(
        id INTEGER PRIMARY KEY,
        apartment_id INTEGER,
        previous_reading INTEGER,
        current_reading INTEGER,
        reading_date TEXT)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS bills(
        id INTEGER PRIMARY KEY,
        apartment_id INTEGER,
        units_used INTEGER,
        unit_price REAL,
        stairs_fee REAL,
        electricity_fee REAL,
        total_amount REAL,
        month TEXT)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS payments(
        id INTEGER PRIMARY KEY,
        apartment_id INTEGER,
        month TEXT,
        electricity_paid REAL,
        water_paid REAL)''')

    Con.commit()
    Con.close()

@app.route("/", methods=['GET', 'POST'])
def home():
    form_to_show = None
    error = None

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_apartment':
            form_to_show = 'add_apartment'
            apartment_id = request.form.get('apartment_id')
            tenant_name = request.form.get('tenant_name')
            meter_number = request.form.get('meter_number')

            if apartment_id and tenant_name and meter_number:
                Con = sql.connect(Db)
                cur = Con.cursor()
                cur.execute("INSERT INTO apartments(apartment_id, tenant_name, meter_number) VALUES (?, ?, ?)",
                            (apartment_id, tenant_name, meter_number))
                Con.commit()
                Con.close()
                return render_template('home.html', apartment_id=apartment_id, tenant_name=tenant_name,
                                       meter_number=meter_number, form_to_show=form_to_show)

        elif action == 'recording_the_meter_reading':
            form_to_show = 'recording_the_meter_reading'
            apartment_id = request.form.get('apartment_id')
            current_reading = request.form.get('current_reading')
            reading_date = request.form.get('reading_date')

            Con = sql.connect(Db)
            cur = Con.cursor()

            cur.execute('''SELECT current_reading FROM meter_readings 
                           WHERE apartment_id = ? ORDER BY reading_date DESC LIMIT 1''', (apartment_id,))
            row = cur.fetchone()
            previous_reading = row[0] if row else request.form.get('previous_reading')

            cur.execute('''INSERT INTO meter_readings(apartment_id, previous_reading, current_reading, reading_date) 
                           VALUES (?, ?, ?, ?)''', (apartment_id, previous_reading, current_reading, reading_date))

            Con.commit()
            Con.close()

            return render_template('home.html', apartment_id=apartment_id, previous_reading=previous_reading,
                                   current_reading=current_reading, reading_date=reading_date,
                                   form_to_show=form_to_show)

        elif action == 'invoice_account':
            form_to_show = 'invoice_account'
            apartment_id = request.form.get('apartment_id')
            unit_price = request.form.get('unit_price')
            stairs_fee = request.form.get('stairs_fee')
            electricity_fee = request.form.get('electricity_fee')
            month = request.form.get('month')

            if not all([apartment_id, unit_price, stairs_fee, electricity_fee, month]):
                error = 'الرجاء تعبئة كل الحقول المطلوبة'
                return render_template('home.html', form_to_show=form_to_show, error=error)

            try:
                apartment_id = int(apartment_id)
                unit_price = float(unit_price)
                stairs_fee = float(stairs_fee)
                electricity_fee = float(electricity_fee)
            except ValueError:
                error = 'تأكد من إدخال أرقام صحيحة'
                return render_template('home.html', form_to_show=form_to_show, error=error)

            Con = sql.connect(Db)
            cur = Con.cursor()
            cur.execute('''SELECT previous_reading, current_reading FROM meter_readings
                           WHERE apartment_id = ? ORDER BY reading_date DESC LIMIT 1''', (apartment_id,))
            row = cur.fetchone()

            if not row:
                error = 'لا توجد قراءة سابقة لهذه الشقة'
                return render_template('home.html', form_to_show=form_to_show, error=error)

            previous_reading, current_reading = row
            units_used = current_reading - previous_reading
            total_amount = (units_used * unit_price) + stairs_fee + electricity_fee

            cur.execute('''INSERT INTO bills(apartment_id, units_used, unit_price, stairs_fee,
                           electricity_fee, total_amount, month)
                           VALUES (?, ?, ?, ?, ?, ?, ?)''',
                        (apartment_id, units_used, unit_price, stairs_fee, electricity_fee, total_amount, month))

            Con.commit()
            Con.close()

            return render_template('home.html', apartment_id=apartment_id, units_used=units_used,
                                   unit_price=unit_price, stairs_fee=stairs_fee, electricity_fee=electricity_fee,
                                   total_amount=total_amount, month=month, form_to_show=form_to_show)

        elif action == 'payment_registration':
            form_to_show = 'payment_registration'
            apartment_id = request.form.get('apartment_id')
            electricity_paid = request.form.get('electricity_paid') or 0
            water_paid = request.form.get('water_paid') or 0

            Con = sql.connect(Db)
            cur = Con.cursor()

            cur.execute("SELECT month FROM bills WHERE apartment_id = ? ORDER BY id DESC LIMIT 1", (apartment_id,))
            result = cur.fetchone()
            month = result[0] if result else T.datetime.now().strftime('%m')

            cur.execute('''INSERT INTO payments(apartment_id, month, electricity_paid, water_paid)
                           VALUES (?, ?, ?, ?)''',
                        (apartment_id, month, electricity_paid, water_paid))

            Con.commit()
            Con.close()

            return render_template('home.html', apartment_id=apartment_id, month=month,
                                   electricity_paid=electricity_paid, water_paid=water_paid,
                                   form_to_show=form_to_show)

        elif action == 'apartment_statement':
            form_to_show = 'apartment_statement'
            apartment_id = request.form.get('apartment_id')

            Con = sql.connect(Db)
            cur = Con.cursor()

            meter = cur.execute('''SELECT current_reading, reading_date FROM meter_readings
                                   WHERE apartment_id = ? ORDER BY id DESC LIMIT 1''',
                                (apartment_id,)).fetchall()

            bill = cur.execute('''SELECT total_amount, month FROM bills
                                  WHERE apartment_id = ? ORDER BY id DESC LIMIT 1''',
                               (apartment_id,)).fetchall()

            pay = cur.execute('''SELECT electricity_paid, water_paid FROM payments
                                 WHERE apartment_id = ? ORDER BY id DESC LIMIT 1''',
                              (apartment_id,)).fetchall()

            Con.close()
            return render_template('home.html', form_to_show=form_to_show, meter=meter, bill=bill,
                                   pay=pay, apartment_id=apartment_id)

    return render_template('home.html', form_to_show=form_to_show, error=error)

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=9000)
