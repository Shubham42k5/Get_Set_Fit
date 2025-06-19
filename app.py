from flask import Flask, render_template, request, redirect, session, jsonify
import pymysql
import hashlib
import requests

app = Flask(__name__)
app.secret_key = 'secret123'  # session secret key

# MySQL Configuration
conn = pymysql.connect(
    host='localhost',
    user='root',
    password='',
    database='get_set_fit'
)
cursor = conn.cursor()

# --- Your existing routes here (login, signup, dashboard, etc.) ---

# Home route (login page)
@app.route('/')
def login_page():
    return render_template('login.html')

# Signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()

        try:
            cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
            conn.commit()

            # Get the user ID of the newly created user
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            session['user_id'] = user[0]
            session['user'] = name

            return redirect('/collect-data')
        except Exception as e:
            print(f"Error during signup: {e}")
            return "User already exists or an error occurred"

    return render_template('signup.html')


# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()

        cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user[0]
            session['user'] = user[1]
            return redirect('/dashboard')
        else:
            return "Invalid credentials"
    return render_template('login.html')

# User Data Collection route
@app.route('/collect-data', methods=['GET', 'POST'])
def collect_data():
    if 'user_id' not in session:
        return redirect('/')

    if request.method == 'POST':
        gender = request.form['gender']
        age = request.form['age']
        height = request.form['height']
        weight = request.form['weight']
        fat_percentage = request.form['fat_percentage']
        goal = request.form['goal']

        cursor.execute("""
            INSERT INTO user_data (user_id, gender, age, height, weight, fat_percentage, goal)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (session['user_id'], gender, age, height, weight, fat_percentage, goal))
        conn.commit()

        return redirect('/dashboard')

    return render_template('collect_data.html')

# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user_id = session['user_id']

        # Get user's name from `users` table
        cursor.execute("SELECT name FROM users WHERE id = %s", (user_id,))
        user_result = cursor.fetchone()
        user_name = user_result[0] if user_result else 'User'

        # Get user's fitness data from `user_data` table
        cursor.execute("""
            SELECT gender, age, height, weight, fat_percentage, goal, manual_goal 
            FROM user_data WHERE user_id = %s
        """, (user_id,))
        user_data = cursor.fetchone()

        if user_data:
            gender, age, height, weight, fat_percentage, goal, manual_goal = user_data

            # Calculate BMI
            height_m = float(height) / 100
            bmi = round(float(weight) / (height_m ** 2), 1)

            # Determine weight status
            if bmi < 18.5:
                bmi_status = "Underweight"
            elif bmi > 25:
                bmi_status = "Overweight"
            else:
                bmi_status = "Normal"

            # Final goal to display: use manual if set
            display_goal = manual_goal if manual_goal else goal

            return render_template(
                'dashboard.html',
                name=user_name,
                gender=gender,
                age=age,
                height=height,
                weight=weight,
                fat=fat_percentage,
                goal=display_goal,
                bmi=bmi,
                bmi_status=bmi_status
            )
        else:
            return "User data not found. Please complete signup properly."
    else:
        return redirect('/')

# plantype helper function
def determine_plan_type(weight, height):
    height_m = float(height) / 100
    bmi = float(weight) / (height_m ** 2)

    if bmi > 25:
        return 'fat loss'
    elif bmi < 18.5:
        return 'muscle gain'
    else:
        return 'maintenance'

# Workout plans
@app.route('/workout-plans')
def workout_plans():
    if 'user_id' not in session:
        return redirect('/')

    user_id = session['user_id']
    cursor.execute("SELECT weight, height, gender FROM user_data WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()

    if not result:
        return redirect('/collect-data')

    weight, height, gender = result

    cursor.execute("SELECT manual_goal FROM user_data WHERE user_id = %s", (user_id,))
    manual = cursor.fetchone()[0]

    if manual:
        plan_type = manual.lower()
    else:
        plan_type = determine_plan_type(weight, height)

    workout_data = {
        'fat loss': {
            'male': [
                '🏃 HIIT: 4x/week (20–30 mins)',
                '💪 Strength: Full-body circuits 3x/week',
                '🧘 Yoga: Power yoga 2x/week',
                '🚴 Cardio: 2 cycling sessions/week',
                '📅 Rest: 1 active recovery day'
            ],
            'female': [
                '🏃 Dance Cardio or Zumba: 4x/week',
                '💪 Bodyweight circuits 3x/week',
                '🧘 Yoga: Vinyasa or Pilates 3x/week',
                '🚶 Walking: Evening brisk walks 3x/week',
                '📅 Rest: 1–2 gentle yoga days'
            ]
        },
        'muscle gain': {
            'male': [
                '🏋️‍♂️ Push/Pull/Legs split 5x/week',
                '💪 Progressive overload training',
                '🧘 Yoga: Stretch-focused post-lift yoga 2x/week',
                '🚴 Light cardio: 1x/week to maintain stamina',
                '📅 Rest: 1 full rest day/week'
            ],
            'female': [
                '🏋️‍♀️ Glutes + Legs focused: 3x/week',
                '💪 Upper body + core: 2x/week',
                '🧘 Yoga: Flexibility and breath control 2x/week',
                '🚶 Walking/Cardio: Light treadmill or elliptical 2x/week',
                '📅 Rest: 1 day'
            ]
        },
        'maintenance': {
            'male': [
                '💪 Strength training 3x/week (Upper, Lower, Full)',
                '🏃 Light cardio or sports 2x/week',
                '🧘 Yoga: Recovery-focused session 1x/week',
                '🚴 Biking/Walks for activity tracking',
                '📅 Balanced routine'
            ],
            'female': [
                '🧘 Yoga or Pilates 2x/week',
                '💪 Moderate strength + toning 3x/week',
                '🏃 Cardio: Zumba or aerobics 2x/week',
                '🚶 Walking: 5k steps/day goal',
                '📅 Light & flexible schedule'
            ]
        }
    }

    workout = workout_data.get(plan_type, {}).get(gender.lower(), [])
    return render_template('workout_plans.html', goal=plan_type.title(), workout=workout)

# Diet plans
@app.route('/diet-plans')
def diet_plans():
    if 'user_id' not in session:
        return redirect('/')

    user_id = session['user_id']
    cursor.execute("SELECT weight, height FROM user_data WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()

    if not result:
        return redirect('/collect-data')

    weight, height = result

    cursor.execute("SELECT manual_goal FROM user_data WHERE user_id = %s", (user_id,))
    manual = cursor.fetchone()[0]

    if manual:
        plan_type = manual.lower()
    else:
        plan_type = determine_plan_type(weight, height)

    diet_data = {
        'fat loss': [
            '🔸 Breakfast: Egg whites, oats, black coffee',
            '🔸 Lunch: Grilled chicken salad, olive oil dressing',
            '🔸 Snack: Apple or cucumber slices',
            '🔸 Dinner: Steamed veggies, quinoa, lemon water',
            '💧 Hydration: 3L water per day',
            '❗ Avoid: Sugar, fried food, sodas'
        ],
        'muscle gain': [
            '🍳 Breakfast: 4 boiled eggs, oats with peanut butter',
            '🍛 Lunch: Chicken breast, brown rice, avocado',
            '🥤 Snack: Protein shake + banana',
            '🥘 Dinner: Fish, sweet potatoes, veggies',
            '💊 Supplements: Whey protein, creatine, multivitamin',
            '💧 Hydration: 3.5L water per day'
        ],
        'maintenance': [
            '🥣 Breakfast: Greek yogurt, nuts, berries',
            '🍱 Lunch: Lean protein, mixed grains, green salad',
            '🍌 Snack: Fruit or smoothie',
            '🥗 Dinner: Stir fry vegetables + tofu',
            '💧 Water: 2.5–3L per day',
            '✅ Balanced intake: 40% carbs, 30% protein, 30% fats'
        ]
    }

    diet = diet_data.get(plan_type)
    return render_template('diet_plans.html', goal=plan_type.title(), diet=diet)

# Set goal route
@app.route('/set-goal', methods=['GET', 'POST'])
def set_goal():
    if 'user_id' not in session:
        return redirect('/')

    if request.method == 'POST':
        new_goal = request.form['goal']
        cursor.execute("UPDATE user_data SET manual_goal = %s WHERE user_id = %s", (new_goal, session['user_id']))
        conn.commit()
        return redirect('/dashboard')

    return render_template('set_goal.html')

# Calorie calculator route
@app.route('/calorie-calculator')
def calorie_calculator():
    if 'user_id' not in session:
        return redirect('/')

    cursor.execute("SELECT gender, age, height, weight FROM user_data WHERE user_id = %s", (session['user_id'],))
    result = cursor.fetchone()

    if not result:
        return redirect('/collect-data')

    gender, age, height, weight = result

    # BMR using Mifflin-St Jeor Equation
    if gender.lower() == 'male':
        bmr = 10 * weight + 6.25 * height - 5 * int(age) + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * int(age) - 161

    maintenance = round(bmr * 1.5)  # moderate activity
    fat_loss = maintenance - 500
    muscle_gain = maintenance + 300

    # simple macros: 40% carbs, 30% protein, 30% fat
    def macros(cal):
        return {
            'Calories': cal,
            'Carbs (g)': round((0.4 * cal) / 4),
            'Protein (g)': round((0.3 * cal) / 4),
            'Fats (g)': round((0.3 * cal) / 9)
        }

    data = {
        'Maintenance': macros(maintenance),
        'Fat Loss': macros(fat_loss),
        'Muscle Gain': macros(muscle_gain)
    }

    return render_template('calorie_calculator.html', data=data)

# Home route
@app.route('/home')
def home():
    return render_template('index.html')

# --- Chatbot Integration ---

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

def chat_with_ollama(prompt):
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": "mistral",
            "prompt": prompt,
            "stream": False
        }, timeout=200)  # timeout in seconds

        if response.status_code == 200:
            return response.json().get("response", "No response from Ollama.")
        else:
            return f"Error: {response.status_code}, {response.text}"
    except requests.exceptions.Timeout:
        return "Error: Request to Ollama timed out."
    except Exception as e:
        return f"Error: {str(e)}"

# Chatbot frontend page
@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

# Chatbot API route (called by frontend JS)
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")

    if not user_message.strip():
        return jsonify({"response": "Please enter a message."})

    response = chat_with_ollama(user_message)
    return jsonify({"response": response})

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

#musclemap route
@app.route('/muscle-map')
def muscle_map():
    return render_template('muscle_map.html')


# excercise_muscle route
@app.route('/exercises/<muscle>')
def muscle_exercises(muscle):
    # You can later fetch from DB
    example_exercises = {
        "chest": ["Bench Press", "Push-ups"],
        "arms": ["Bicep Curls", "Tricep Dips"],
        "abs": ["Plank", "Crunches"],
        "legs": ["Squats", "Lunges"],
        "back": ["Deadlifts", "Pull-ups"]
    }
    return render_template("exercises.html", muscle=muscle, exercises=example_exercises.get(muscle.lower(), []))

#profile route
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect('/')

    user_id = session['user_id']

    cursor.execute("SELECT gender, age, height, weight, fat_percentage, goal FROM user_data WHERE user_id = %s", (user_id,))
    data = cursor.fetchone()

    if data:
        gender, age, height, weight, fat_percentage, goal = data

        height_m = float(height) / 100
        bmi = round(float(weight) / (height_m ** 2), 1)

        if bmi < 18.5:
            bmi_status = "Underweight"
        elif bmi > 25:
            bmi_status = "Overweight"
        else:
            bmi_status = "Normal"

        return render_template("profile.html", gender=gender, age=age, height=height, weight=weight, fat=fat_percentage, goal=goal, bmi=bmi, bmi_status=bmi_status)

    return "Profile data not found."


if __name__ == '__main__':
    app.run(debug=True)
