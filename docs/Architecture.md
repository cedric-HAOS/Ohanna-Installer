# Architecture

## Objectif

**Ohanna-Installer** est l'installateur officiel de l'écosystème **Ohanna**.

Sa responsabilité est d'installer, de mettre à jour et de désinstaller les composants officiels de la plateforme de manière fiable, reproductible et sécurisée.

Il ne contient aucune logique métier propre aux composants qu'il installe.

---

# Position dans l'écosystème

```text
                     Ohanna Platform
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
 Ohanna-Agent       Ohanna-Vision      Ohanna-Installer
    Observe             Visualise          Déploie
```

Les responsabilités sont volontairement séparées.

| Projet           | Responsabilité                                                    |
| ---------------- | ----------------------------------------------------------------- |
| Ohanna-Platform  | Définit l'architecture, les contrats publics et le Design System. |
| Ohanna-Agent     | Observe l'infrastructure et produit des observations.             |
| Ohanna-Vision    | Présente les données collectées.                                  |
| Ohanna-Installer | Gère le cycle de vie des composants.                              |

Cette séparation limite le couplage entre les projets et facilite leur évolution indépendante.

---

# Responsabilités

Ohanna-Installer est responsable de :

* vérifier les prérequis de l'environnement ;
* télécharger les releases officielles ;
* installer les composants ;
* générer les fichiers de configuration ;
* créer les services système ;
* mettre à jour les composants installés ;
* désinstaller proprement la plateforme.

Il n'est **pas** responsable :

* de collecter des observations ;
* de superviser l'infrastructure ;
* d'exposer une interface utilisateur ;
* d'exécuter des plugins métier ;
* de remplacer les fonctionnalités d'Ohanna-Agent ou d'Ohanna-Vision.

---

# Principes d'architecture

## Une responsabilité unique

Chaque composant de l'écosystème possède une responsabilité clairement identifiée.

Ohanna-Installer se limite exclusivement à l'installation et à la maintenance des composants officiels.

---

## Releases officielles uniquement

Les installations reposent exclusivement sur les releases officielles publiées.

Le projet ne déploie jamais directement une branche Git de développement.

```text
GitHub Release
        │
        ▼
Téléchargement
        │
        ▼
Installation
```

Cette approche garantit des installations reproductibles et identiques entre les environnements.

---

## Aucun couplage métier

Ohanna-Installer ne connaît pas le fonctionnement interne d'Ohanna-Agent ni d'Ohanna-Vision.

Il orchestre leur installation sans embarquer leur logique métier.

Chaque composant reste autonome et peut évoluer indépendamment.

---

## Simplicité

La première version du projet privilégie une approche volontairement simple.

Trois commandes constituent le périmètre fonctionnel :

```text
ohanna install
ohanna update
ohanna uninstall
```

Les fonctionnalités d'administration avancées seront introduites dans des versions ultérieures.

---

# Processus d'installation

Le processus suit les étapes suivantes :

```text
Vérification de l'environnement
               │
               ▼
Téléchargement des releases
               │
               ▼
Installation des composants
               │
               ▼
Génération des configurations
               │
               ▼
Installation des services
               │
               ▼
Validation finale
```

Chaque étape est validée avant de poursuivre afin de garantir une installation cohérente.

---

# Gestion des composants

Dans sa première version, Ohanna-Installer gère les composants suivants :

* Ohanna-Agent
* Ohanna-Vision

Chaque composant est installé indépendamment.

Cette architecture permettra d'ajouter de nouveaux composants officiels sans remettre en cause le fonctionnement général de l'installateur.

---

# Compatibilité

La version 1.0.0 cible les systèmes Linux utilisant **systemd**.

Les environnements de développement Windows restent pris en charge pour le développement et les tests du projet.

---

# Évolutivité

L'architecture a été pensée pour permettre l'ajout progressif de nouvelles fonctionnalités sans modifier les principes fondateurs.

Les évolutions envisagées comprennent notamment :

* installation sélective des composants ;
* sauvegarde et restauration ;
* diagnostic de la plateforme ;
* mise à jour automatique ;
* support de nouveaux environnements de déploiement.

Ces évolutions devront préserver les principes suivants :

* responsabilité unique ;
* faible couplage ;
* simplicité ;
* installations reproductibles ;
* compatibilité avec les releases officielles.

---

# Conclusion

Ohanna-Installer constitue le point d'entrée officiel de l'écosystème Ohanna.

Son rôle est de rendre le déploiement, la mise à jour et la désinstallation des composants aussi simples que possible, tout en laissant à chaque produit la responsabilité de son propre domaine fonctionnel.
