# com_menu

Správa menu a navigačních položek pro frontend šablony.

## Metadata

| Pole | Hodnota |
| :--- | :--- |
| Typ | `component` |
| Verze | `0.1.7` |
| Vendor | `klucon` |
| Extension ID | `klucon/com_menu` |
| Kategorie | `navigation` |
| Licence | MIT |
| Core minimum | `0.1.0` |
| Python | `>=3.12` |
| Entry point | `src.components.com_menu` |
| Admin URL | `/admin/com_menu` |

## Účel

Menu je marketplace rozšíření pro KLUCON CMS. Balíček je určený pro instalaci přes `/admin/marketplace` a musí projít validací manifestu, checksumu a podpisu.

## Struktura

```text
src/**/com_menu/
├── manifest.json
├── __init__.py
├── i18n/
└── ...
```

Manifest používá schema `1.0`, deklaruje typ `component`, kompatibilitu s core, i18n doménu `com_menu` a bezpečnostní capabilities. Implementace obsahuje admin routes podle manifestu.

## Balíčkování

Release ZIP se staví z `src/**/com_menu/manifest.json` pomocí GitHub Actions workflow `.github/workflows/release-package.yml`. Do balíčku nepatří cache, `.git`, lokální ZIP artefakty ani dočasné soubory.

## Instalace

1. Publikuj ZIP a metadata do marketplace serveru.
2. V CMS otevři `/admin/marketplace`.
3. Vyber `com_menu` a instaluj verzi `0.1.7`.
4. Po instalaci ověř záznam v příslušné tabulce `installed_*`.

## Poznámky k verzi

Aktualizace dokumentace a rebuild balíčku pro GitHub distribuci.
