# CHANGELOG

Toutes les évolutions notables de ce projet seront documentées dans ce fichier.

Le format s'inspire de **Keep a Changelog** et respecte le **Versioning Sémantique (SemVer)**.

---

# [Unreleased]

## Modifié

* Passage du runtime minimal à Python 3.13.
* Ciblage du manifeste Ohana-Platform `v1.0.1`.
* Alignement sur Ohana-Agent et Ohana-Vision `v1.1.1`.
* Utilisation de comptes systemd dédiés à chaque composant.
* Modernisation des métadonnées de licence du package.

---

# [1.0.0] - À venir

Première version officielle d'**Ohana-Installer**.

## Ajouté

### Projet

* Création du dépôt Ohana-Installer.
* Mise en place de l'architecture du projet.
* Packaging Python.
* Commande CLI `ohana`.

### Installation

* Vérification de l'environnement.
* Téléchargement des releases officielles.
* Installation d'Ohana-Agent.
* Installation d'Ohana-Vision.
* Génération des fichiers de configuration.
* Installation des services système.
* Validation automatique de l'installation.

### Mise à jour

* Détection des versions installées.
* Recherche des nouvelles releases.
* Mise à jour des composants.
* Redémarrage automatique des services.
* Validation de la mise à jour.

### Désinstallation

* Arrêt des services.
* Désinstallation des composants.
* Suppression des services système.
* Nettoyage de l'installation.
* Suppression optionnelle des fichiers de configuration.

### Documentation

* README.
* ROADMAP.
* CHANGELOG.
* Documentation d'architecture.
* Guides d'installation, de mise à jour et de désinstallation.

### Qualité

* Tests unitaires.
* Tests d'intégration.
* Audit final.
* Première release officielle.

---

# Versions antérieures

Aucune.
