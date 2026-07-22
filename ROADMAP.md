# ROADMAP

Ce document présente la feuille de route officielle d'**Ohanna-Installer**.

L'objectif du projet est de fournir un installateur simple, fiable et reproductible pour l'ensemble de l'écosystème Ohanna.

---

# Version 1.0.0

## 1. Initialisation du projet

### 1.1 Structure du dépôt

* Création de l'architecture du projet.
* Organisation des modules.
* Configuration du packaging Python.

### 1.2 Interface en ligne de commande

* Commande `ohanna`.
* Gestion des arguments.
* Aide intégrée.
* Affichage de la version.

### 1.3 Qualité logicielle

* Configuration de Ruff.
* Configuration de Pytest.
* Couverture de tests initiale.
* Intégration continue.

---

## 2. Installation

### 2.1 Vérification de l'environnement

* Vérification du système d'exploitation.
* Vérification de Python.
* Vérification de Git.
* Vérification de la connectivité réseau.
* Vérification des prérequis.

### 2.2 Téléchargement des composants

* Détection des releases officielles.
* Téléchargement sécurisé.
* Vérification de la version.

### 2.3 Installation d'Ohanna-Agent

* Installation du package.
* Création de l'environnement Python.
* Génération de la configuration.
* Installation du service système.

### 2.4 Installation d'Ohanna-Vision

* Installation du package.
* Génération de la configuration.
* Installation du service système.

### 2.5 Validation

* Vérification du démarrage des services.
* Vérification des versions installées.
* Validation finale de l'installation.

---

## 3. Mise à jour

### 3.1 Détection

* Identification des versions installées.
* Recherche des nouvelles releases.

### 3.2 Mise à jour

* Téléchargement des nouvelles versions.
* Mise à jour des composants.
* Redémarrage des services.

### 3.3 Validation

* Vérification du bon fonctionnement.
* Confirmation de la réussite de la mise à jour.

---

## 4. Désinstallation

### 4.1 Arrêt

* Arrêt des services.
* Désactivation des services système.

### 4.2 Suppression

* Désinstallation des composants.
* Suppression des environnements Python.
* Nettoyage des fichiers installés.

### 4.3 Nettoyage

* Suppression optionnelle des fichiers de configuration.
* Vérification de la désinstallation complète.

---

## 5. Documentation

### 5.1 Documentation utilisateur

* README.
* Guide d'installation.
* Guide de mise à jour.
* Guide de désinstallation.

### 5.2 Documentation technique

* Architecture.
* Organisation du code.
* Contribution.

---

## 6. Validation finale

### 6.1 Tests

* Tests unitaires.
* Tests d'intégration.
* Validation des trois commandes principales.

### 6.2 Audit

* Audit de qualité.
* Audit des dépendances.
* Vérification du packaging.

### 6.3 Release

* Publication de la release officielle.
* Génération des artefacts.
* Publication de la documentation.

---

# Évolutions futures

Les fonctionnalités suivantes sont volontairement reportées après la version 1.0.0 :

* Sauvegarde et restauration.
* Retour arrière (rollback).
* Diagnostic (`doctor`).
* État de la plateforme (`status`).
* Gestion des journaux.
* Installation sélective des composants.
* Mise à jour automatique planifiée.
* Support de Docker.
* Support de Kubernetes.
* Déploiement multi-sites.

La priorité de la version **1.0.0** est de fournir un installateur officiel simple, fiable et stable pour l'écosystème Ohanna.
