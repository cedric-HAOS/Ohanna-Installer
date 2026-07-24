# CHANGELOG

Toutes les évolutions notables de ce projet seront documentées dans ce fichier.

Le format s'inspire de **Keep a Changelog** et respecte le **Versioning Sémantique (SemVer)**.

---

# [Unreleased]

---

# [1.0.0] - 2026-07-24

Première version officielle d'**Ohana-Installer**.

## Modifié

* Passage du runtime minimal à Python 3.13.
* Ciblage du manifeste Ohana-Platform `v1.0.1`.
* Alignement sur Ohana-Agent et Ohana-Vision `v1.1.1`.
* Utilisation de comptes systemd dédiés à chaque composant.
* Modernisation des métadonnées de licence du package.

## Ajouté

### Projet

* Création du dépôt Ohana-Installer.
* Mise en place de l'architecture du projet.
* Packaging Python.
* Commande CLI `ohana`.

### Installation

* Vérification de l'environnement.
* Découverte automatique de la dernière release stable d'Ohana-Platform.
* Vérification SHA-256 du manifeste, des wheels et des configurations avant écriture.
* Téléchargement des releases officielles épinglées par le manifeste Platform.
* Installation d'Ohana-Agent.
* Installation d'Ohana-Vision.
* Génération des fichiers de configuration.
* Installation des services système.
* Validation automatique de l'installation.
* Confirmation négative par défaut et option d'automatisation `--yes`.

### Mise à jour

* Détection des versions installées.
* Recherche des nouvelles releases.
* Absence de modification lorsque les versions sont déjà à jour.
* Refus des rétrogradations automatiques.
* Mise à jour des composants.
* Redémarrage automatique des services.
* Validation de la mise à jour.
* Confirmation négative par défaut et option d'automatisation `--yes`.

### Désinstallation

* Arrêt des services.
* Désinstallation des composants.
* Suppression des services système.
* Nettoyage de l'installation.
* Conservation des fichiers de configuration locale.
* Confirmation négative par défaut et option d'automatisation `--yes`.

### Documentation

* README.
* ROADMAP.
* CHANGELOG.
* Documentation d'architecture.
* Guide d'installation sur Raspberry Pi, de mise à jour et de désinstallation.

### Qualité

* Tests unitaires.
* Tests d'intégration.
* Audit final.
* Première release officielle.

---

# Versions antérieures

Aucune.
