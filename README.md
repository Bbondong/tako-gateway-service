# Tako Gateway Service

## Description

Le **Tako Gateway Service** est le point d'entrée unique pour toutes les requêtes externes de l'application mobile Tako. Il agit comme un proxy inverse, acheminant les requêtes vers les microservices backend appropriés (Auth, Transactions, Payment). Ce service est crucial pour l'orchestration des communications et la gestion centralisée des requêtes.

## Fonctionnalités

- **Routage intelligent** : Redirige les requêtes entrantes vers les microservices cibles en fonction de l'URL.
- **Proxy transparent** : Transmet les en-têtes, les méthodes HTTP et les corps de requêtes sans modification.
- **Health Check** : Fournit un endpoint pour vérifier l'état de fonctionnement du service.

## Architecture

Le service est développé en Python avec Flask et suit une architecture modulaire :

```text
gateway_service/
├── app.py              # Point d'entrée principal de l'application Flask
├── requirements.txt    # Dépendances Python
└── src/
    ├── __init__.py
    ├── routes/         # Contient les définitions des routes et la logique de proxy
    │   └── gateway_routes.py
    └── utils/          # Utilitaires (actuellement vide, pour de futures extensions)
```

## Configuration

Les URLs des microservices cibles sont configurées dans `src/routes/gateway_routes.py`. En production, il est recommandé d'utiliser des variables d'environnement ou un système de gestion de configuration pour ces URLs.

```python
SERVICE_URLS = {
    "auth": "http://localhost:5001", # URL du service d'authentification
    "transactions": "http://localhost:5002", # URL du service de transactions
    "payment": "http://localhost:5003" # URL du service de paiement
}
```

## Installation et Exécution (Développement)

1.  **Cloner le dépôt** :
    ```bash
    git clone https://github.com/Bbondong/tako-gateway-service.git
    cd tako-gateway-service
    ```

2.  **Créer un environnement virtuel et installer les dépendances** :
    ```bash
    python -m venv venv
    source venv/bin/activate  # Sur Windows: .\venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Lancer le service** :
    ```bash
    python app.py
    ```
    Le service sera accessible sur `http://localhost:5000`.

## Endpoints API

-   `GET /` : Health check du service Gateway.
-   `/<service_name>/<path:path>` : Proxy vers le service spécifié (ex: `/auth/register`, `/transactions/rides`).

## Déploiement

Pour un déploiement en production, il est recommandé d'utiliser Docker et un serveur WSGI comme Gunicorn. Un `Dockerfile` sera ajouté ultérieurement pour faciliter ce processus.

## Contribution

Les contributions sont les bienvenues. Veuillez suivre les directives de contribution et soumettre des pull requests.

## Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## Client mobile API

`/api/v1/*` proxies to `AUTH_SERVICE_URL/api/v1/*`. Configure the same
`TAKO_API_KEY_INTER_SERVICES` here as `TAKO_API_KEY` on the auth service.
Versioned account endpoints verify bearer JWT in the auth service. Do not embed
`TAKO_CLIENT_API_KEY` in a mobile application. Existing unversioned routes retain
that legacy key requirement. Set `TAKO_WEB_ORIGINS` to a comma-separated list
of allowed browser origins if using Flutter Web. The gateway and auth service
must be deployed together for the versioned routes to work.
