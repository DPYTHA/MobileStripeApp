from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import logging
import stripe
import os

# Configuration des logs
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialisation de l'application Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://pytha:Pytha1991@localhost/AppMobile')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)

# Connexion à la base de données PostgreSQL
db = SQLAlchemy(app)

# Configuration de Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "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")

# Modèle utilisateur
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    numero = db.Column(db.String(20))
    pays = db.Column(db.String(100))
    password_hash = db.Column(db.Text, nullable=False)
    date_inscription = db.Column(db.DateTime, default=datetime.utcnow)
    abonnement_active = db.Column(db.Boolean, default=False)
    trial_expiry = db.Column(db.DateTime, nullable=True)  # Heure de fin de l'essai
    has_used_trial = db.Column(db.Boolean, default=False)  # Marque si l'utilisateur a utilisé l'essai gratuit

# Modèle Bourses
class Bourse(db.Model):
    __tablename__ = 'bourses'
    id = db.Column(db.Integer, primary_key=True)
    nom_bourse = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    pays = db.Column(db.String(100), nullable=False)
    niveau_etude = db.Column(db.String(50), nullable=False)
    date_limite = db.Column(db.Date, nullable=False)
    lien_bourse = db.Column(db.String(255), nullable=False)
    age_min = db.Column(db.Integer, nullable=True)  # Ajout de l'âge minimum
    age_max = db.Column(db.Integer, nullable=True)  # Ajout de l'âge maximum

    def as_dict(self):
        return {
            'id': self.id,
            'nom_bourse': self.nom_bourse,
            'description': self.description,
            'pays': self.pays,
            'niveau_etude': self.niveau_etude,
            'date_limite': self.date_limite,
            'lien_bourse': self.lien_bourse,
            'age_min': self.age_min,  # Ajout de l'âge minimum
            'age_max': self.age_max   # Ajout de l'âge maximum
        }

# Création des tables
with app.app_context():
    db.create_all()
    logging.info("Tables créées avec succès !")

# 📌 Inscription utilisateur
@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.json
        if not data or "email" not in data or "password" not in data:
            return jsonify({"error": "Email et mot de passe sont requis"}), 400

        if User.query.filter_by(email=data["email"]).first():
            return jsonify({"error": "Cet email est déjà utilisé"}), 400

        hashed_password = generate_password_hash(data["password"], method='pbkdf2:sha256')
        new_user = User(
            nom=data.get("nom", ""),
            prenom=data.get("prenom", ""),
            email=data["email"],
            numero=data.get("numero", ""),
            pays=data.get("pays", ""),
            password_hash=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "Utilisateur inscrit avec succès"}), 201
    
    except Exception as e:
        logging.error(f"Erreur dans la route /register : {str(e)}")
        return jsonify({"error": "Erreur interne du serveur"}), 500

# 📌 Connexion utilisateur
@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.json
        user = User.query.filter_by(email=data["email"]).first()
        if user and check_password_hash(user.password_hash, data["password"]):
            # Renvoie les données de l'utilisateur
            return jsonify({
                "message": "Connexion réussie",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "nom": user.nom,
                    "prenom": user.prenom,
                    
                  


                    # Ajoutez d'autres champs si nécessaire
                }
            }), 200
        return jsonify({"error": "Email ou mot de passe incorrect"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Vérification de l'accès
@app.route("/check-access", methods=["GET"])
def check_access():
    try:
        email = request.args.get("email")
        if not email:
            return jsonify({"error": "Email requis"}), 400
        
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({"error": "Utilisateur non trouvé"}), 404

        # Vérifie si l'utilisateur a un abonnement premium ou s'il est dans la période d'essai
        has_access = user.abonnement_active or (user.trial_expiry and user.trial_expiry > datetime.utcnow())

        if has_access:
            return jsonify({"access": True}), 200
        
        # Si l'essai a expiré, renvoyer une réponse pour rediriger vers l'abonnement
        logging.info(f"Essai expiré pour l'utilisateur {user.email} à {datetime.utcnow()}")
        return jsonify({
            "access": False,
            "message": "Essai expiré. Veuillez souscrire à un abonnement.",
            "redirect_to_payment": True  # Indique au frontend de rediriger vers la page de paiement
        }), 403

    except Exception as e:
        logging.error(f"Erreur dans la route /check-access : {str(e)}")
        return jsonify({"error": "Erreur interne du serveur"}), 500
    
# 📌 Démarrer l'essai gratuit
# 📌 Démarrer l'essai gratuit
from datetime import datetime, timedelta
from flask import request, jsonify
import logging

@app.route("/start-trial", methods=["POST"])
def start_trial():
    try:
        # Récupération des données JSON
        data = request.json
        
        # Vérification si l'email est dans les données reçues
        if "email" not in data or not data["email"]:
            return jsonify({"error": "Email requis"}), 400

        # Recherche de l'utilisateur dans la base de données
        user = User.query.filter_by(email=data["email"]).first()

        # Si l'utilisateur n'est pas trouvé
        if not user:
            return jsonify({"error": "Utilisateur non trouvé"}), 404

        # Si l'utilisateur a déjà utilisé l'essai gratuit
        if user.has_used_trial:
            return jsonify({"error": "Vous avez déjà utilisé l'essai gratuit , Faites un Abonnement pour Continuer (5$/Mois)"}), 400

        # Activation de l'essai gratuit
        user.trial_expiry = datetime.utcnow() + timedelta(minutes=20)  # Essai de 20 minutes
        user.has_used_trial = True  # Marque l'essai comme utilisé
        db.session.commit()

        return jsonify({
            "message": "Essai gratuit de 20 minutes activé",
            "trial_expiry": user.trial_expiry.isoformat()  # Renvoie la date d'expiration
        }), 200

    except Exception as e:
        logging.error(f"Erreur dans la route /start-trial : {str(e)}")
        return jsonify({"error": "Erreur interne du serveur"}), 500

# 📌 Réinitialiser l'essai (pour les tests uniquement)
@app.route("/reset-trial", methods=["POST"])
def reset_trial():
    try:
        data = request.json
        if "email" not in data:
            return jsonify({"error": "Email requis"}), 400

        user = User.query.filter_by(email=data["email"]).first()
        if not user:
            return jsonify({"error": "Utilisateur non trouvé"}), 404

        user.has_used_trial = False
        user.trial_expiry = None
        db.session.commit()
        return jsonify({"message": "Essai réinitialisé"}), 200
    except Exception as e:
        logging.error(f"Erreur dans la route /reset-trial : {str(e)}")
        return jsonify({"error": "Erreur interne du serveur"}), 500
    

@app.route('/search_bourses', methods=['GET'])
def search_bourses():
    try:
        # Récupérer les paramètres de requête
        niveau_etude = request.args.get('niveau_etude')
        age = request.args.get('age')
        pays = request.args.get('pays')

        # Construire la requête de filtrage
        query = Bourse.query

        # Filtrer par niveau d'étude (si fourni)
        if niveau_etude:
            query = query.filter(Bourse.niveau_etude.ilike(f"%{niveau_etude}%"))

        # Filtrer par âge (si fourni)
        if age:
            age = int(age)  # Convertir l'âge en entier
            query = query.filter(Bourse.age_min <= age, Bourse.age_max >= age)

        # Filtrer par pays (si fourni)
        if pays:
            query = query.filter(Bourse.pays.ilike(f"%{pays}%"))

        # Exécuter la requête et récupérer les résultats
        bourses = query.all()

        # Retourner les résultats au format JSON
        return jsonify([bourse.as_dict() for bourse in bourses])

    except Exception as e:
        logging.error(f"Erreur dans la route /search_bourses : {str(e)}")
        return jsonify({"error": "Erreur interne du serveur"}), 500

# 📌 Création d'une session de paiement Stripe
@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        data = request.get_json()
        customer_email = data.get("email")

        # Crée la session Stripe
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': 'Abonnement Premium'},
                    'unit_amount': 5000,  # 05.00 USD
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url='https://10.12.30.123:5000/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://10.12.30.123:5000/cancel',
            customer_email=customer_email,
        )

        # Renvoie l'URL de paiement au frontend
        return jsonify({'id': session.id, 'url': session.url})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

# 📌 Gestion du succès de paiement
@app.route("/success", methods=["GET"])
def success():
    try:
        session_id = request.args.get("session_id")
        if not session_id:
            return jsonify({"error": "Session de paiement introuvable"}), 400

        # Récupère les détails de la session Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        customer_email = session.customer_email  # Récupère l'email du client

        # Met à jour l'utilisateur dans la base de données
        user = User.query.filter_by(email=customer_email).first()
        if not user:
            return jsonify({"error": "Utilisateur non trouvé"}), 404

        user.abonnement_active = True
        user.trial_expiry = datetime.utcnow() + timedelta(days=30)  # Abonnement actif pendant 30 jours
        db.session.commit()

        return """
        <script>
            alert("Paiement réussi ! Votre abonnement est actif pour 1 mois.");
            window.location.href = "http://192.168.0.103:3000/Home";
        </script>
        """
    except Exception as e:
        logging.error(f"Erreur dans la route /success : {str(e)}")
        return jsonify({"error": str(e)}), 500

# 📌 Annulation de paiement
@app.route("/cancel", methods=["GET"])
def cancel():
    return "Le paiement a été annulé."


# Fonction pour gérer un paiement réussi
def handle_successful_payment(session):
    try:
        # Récupère l'email du client depuis la session Stripe
        customer_email = session.get("customer_email")
        if not customer_email:
            logging.error("Email du client non trouvé dans la session Stripe")
            return

        # Recherche l'utilisateur dans la base de données
        user = User.query.filter_by(email=customer_email).first()
        if not user:
            logging.error(f"Utilisateur avec l'email {customer_email} non trouvé")
            return

        # Active l'abonnement et met à jour la date d'expiration
        user.abonnement_active = True
        user.trial_expiry = datetime.utcnow() + timedelta(days=30)  # Abonnement de 30 jours
        db.session.commit()

        logging.info(f"Abonnement activé pour l'utilisateur {user.email}")

    except Exception as e:
        logging.error(f"Erreur lors de la gestion du paiement réussi : {str(e)}")

# Route pour le webhook Stripe
@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    try:
        # Vérifie la signature du webhook
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv('STRIPE_WEBHOOK_SECRET')
        )
    except ValueError as e:
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError as e:
        return jsonify({"error": "Invalid signature"}), 400

    # Gère l'événement checkout.session.completed
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']  # Récupère les détails de la session
        handle_successful_payment(session)  # Appelle la fonction pour gérer le paiement réussi

    return jsonify({"success": True}), 200
# 🚀 Lancer l'application Flask
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)