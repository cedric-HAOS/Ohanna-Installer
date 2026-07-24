# Ohana-Installer

> Installateur officiel de l'écosystème Ohana.

## Présentation

**Ohana-Installer** est le composant chargé d'installer, de mettre à jour et de désinstaller les produits officiels de l'écosystème **Ohana**.

Il automatise le déploiement d'une plateforme complète à partir des releases officielles publiées sur GitHub, sans contenir la logique métier des composants qu'il installe.

À terme, un nouvel utilisateur doit pouvoir installer une plateforme Ohana entièrement fonctionnelle à l'aide d'une seule commande.

---

# Écosystème

Ohana est composé de cinq projets complémentaires :

| Projet               | Rôle                                                            |
| -------------------- | --------------------------------------------------------------- |
| **Ohana-Platform**  | Architecture, documentation, contrats publics et Design System. |
| **Ohana-Agent**     | Collecte les observations et surveille l'infrastructure.        |
| **Ohana-Vision**    | Visualise les observations, l'état de santé et la topologie.    |
| **Ohana-Installer** | Installe, met à jour et désinstalle les composants officiels.   |
| **Ohana-House**     | Documente le déploiement domestique de référence.               |

Chaque projet possède une responsabilité clairement définie.

---

# Objectifs

Ohana-Installer poursuit quatre objectifs principaux :

* simplifier le déploiement de la plateforme ;
* garantir des installations reproductibles ;
* centraliser les mises à jour des composants ;
* proposer une procédure d'installation identique sur toutes les machines supportées.

---

# Fonctionnalités

La version **1.0.0** fournit trois commandes principales :

```text
ohana install
ohana update
ohana uninstall
```

## Installation

La commande :

```bash
ohana install
```

réalise automatiquement :

* la vérification de l'environnement ;
* le téléchargement des releases officielles ;
* l'installation d'Ohana-Agent ;
* l'installation d'Ohana-Vision ;
* la génération des fichiers de configuration ;
* l'installation des services système ;
* la validation finale de l'installation.

---

## Mise à jour

La commande :

```bash
ohana update
```

recherche les nouvelles releases officielles et met à jour les composants installés.

---

## Désinstallation

La commande :

```bash
ohana uninstall
```

supprime proprement les composants installés ainsi que les services associés.

---

# Philosophie

Ohana-Installer ne contient aucune logique métier.

Il ne surveille pas l'infrastructure.

Il ne collecte pas d'observations.

Il ne fournit aucune interface utilisateur.

Son unique responsabilité consiste à gérer le cycle de vie des composants officiels de l'écosystème Ohana.

Cette séparation garantit un faible couplage entre les différents projets et facilite leur évolution indépendante.

---

# Architecture

Le processus d'installation suit le principe suivant :

```text
GitHub Releases
        │
        ▼
Téléchargement des composants
        │
        ▼
Installation
        │
        ▼
Configuration
        │
        ▼
Création des services
        │
        ▼
Validation
```

Les installations s'appuient exclusivement sur des **releases officielles**, garantissant un déploiement reproductible et indépendant des branches de développement.

---

# Compatibilité

La version 1.0.0 est conçue pour les environnements Linux utilisant **systemd**.

Prérequis : **Python 3.13 ou supérieur**. Cette contrainte correspond au
minimum commun exigé par Ohana-Agent et Ohana-Vision.

Les composants installés sont :

* Ohana-Agent ;
* Ohana-Vision.

---

# Développement

Utiliser Python 3.13 ou supérieur.

Création d'un environnement virtuel :

```bash
python -m venv .venv
```

Activation :

### Linux

```bash
source .venv/bin/activate
```

### Windows

```powershell
.venv\Scripts\Activate.ps1
```

Installation des dépendances :

```bash
pip install -e .
```

Lancement des tests :

```bash
pytest
```

---

# Documentation

La documentation du projet est disponible dans le répertoire `docs/`.

Les principales ressources sont :

* `ROADMAP.md`
* `CHANGELOG.md`
* documentation d'architecture
* guides d'installation

---

# Licence

Ce projet est distribué sous licence **MIT**.

Cette base reste volontairement concise et centrée sur la mission d'Ohana-Installer, en cohérence avec les README des autres projets de l'écosystème.
