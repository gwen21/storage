# storage-minio

Service permettant le stockage de données avec Minio (minio.io)

## Principe

* La gestion des lectures/écritures se fait à travers l'API du service minio (port 9000)
* Un service intermédiaire (minio_controller) reçoit les notifications émises par minio, et les convertit en messages WAMP pour crossbar

## Tests

Utiliser le client minio pour effectuer les ajouts/suppressions de fichiers (objets) et répertoires (buckets)

* wget https://dl.minio.io/client/mc/release/linux-amd64/mc
* chmod +x mc
* mc config host add minio http://eolebase.ac-test.fr:9000 zephir zephir123 S3v4
* mc ls minio

## abonnement aux messages

* les services qui veulent recevoir des notifications sur les fichiers doivent souscrire à 'v1.storage.event'

Pour visualiser les messages, un programme listener.py est fourni (à lancer manuellement dans le conteneur : "python3 /listener.py")

## Todo / interrogations

* Comment gérer les autorisations (utilisateur fixe, gérer via un client/service ?)
* séparer le controlleur et le service minio pour permettre la scalabilité ?
* Comment gérer la reconnexion automatique à crossbar ?
* gestion des erreurs (logs/publication d'un évènement ?)

## URLs de test (API)

* les URLs gérées par le controlleur sont sur l'endpoint /storage
* lister les 'buckets' (conteneur de fichiers) : curl <server>:30005/storage/files/
* lister les fichiers d'une bucket  : curl <server>:30005/storage/files/<nom_bucket>
* Récupérer le contenu d'un fichier : curl <server>:30005/storage/files/<nom_bucket>/<nom_fichier>
* Ajouter un fichier dans un bucket (crée le bucket si besoin) : curl -X POST -F files=@/<chemin_fichier> <server>:30005/storage/files/<nom_bucket>
