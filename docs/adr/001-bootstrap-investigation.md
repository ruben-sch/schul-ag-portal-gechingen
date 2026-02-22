# ADR 001: Bootstrap als CSS Framework

## Status
PROPOSED

## Context
Das Projekt benötigt ein stabiles und responsives Layout. Die aktuelle CSS-Konfiguration soll vereinfacht werden, um die Wartbarkeit und Anpassbarkeit zu verbessern.

## Decision
Untersuchung der Eignung von Bootstrap als CSS Framework für das Projekt.

## Investigation Results

### 1. Performance-Vergleich

#### Bootstrap Performance
- **Initial Load**: Bootstrap (minified) ca. 29 KB
- **CSS Only**: ca. 25 KB (bei Custom Build möglich)
- **Runtime Performance**: Minimal Impact durch reine CSS-Klassen
- **Rendering**: Schnelle Rendering-Zeit durch vorgefertigte Klassen

#### Alternatives
- **Tailwind CSS**: Ca. 40 KB (unoptimiert), aber bessere Tree-Shaking möglich
- **Custom CSS**: Abhängig von Implementierung, oft größer wenn alle Features benötigt werden

**Fazit**: Bootstrap bietet gutes Preis-Leistungs-Verhältnis mit moderater Dateigröße.

### 2. Bundle-Größe und Optimierung

#### Bootstrap Optimierungsmöglichkeiten
- **Custom Build**: Nur benötigte Komponenten einbinden
  - Reduktion auf 10-15 KB möglich
  - Entfernen ungenutzter Utilities
- **PurgeCSS/PurgeBootstrap**: Automatische Entfernung ungenutzter Styles
  - Weitere Reduktion auf 8-12 KB erreichbar
- **Gzip Kompression**: Ca. 70% Reduktion der übertragenen Größe

#### Vergleich
| Framework | Unkomprimiert | Mit Gzip | Custom Build + Gzip |
|-----------|---------------|----------|-------------------|
| Bootstrap | 25 KB | 7 KB | 3-5 KB |
| Tailwind | 40 KB | 10 KB | 5-8 KB |
| Custom | Variabel | Variabel | Variabel |

**Fazit**: Bootstrap ermöglicht aggressive Optimierung durch modularen Aufbau.

### 3. Customization und Responsive Design

#### Responsive Web Design Features
**Bootstrap bietet:**
- **12-Spalten Grid System**: Bewährtes, flexibles Layout-System
- **Breakpoints**: xs, sm, md, lg, xl, xxl vordefiniert
  - xs: <576px
  - sm: ≥576px
  - md: ≥768px
  - lg: ≥992px
  - xl: ≥1200px
  - xxl: ≥1400px
- **Responsive Utilities**: 
  - Display-Eigenschaften (d-none, d-md-block, etc.)
  - Spacing (padding/margin) mit Breakpoint-Support
  - Text-Ausrichtung pro Breakpoint
- **Flexbox Integration**: Einfache Flex-Utilities für responsive Layouts

#### Customization Möglichkeiten
- **SASS Variables**: Alle Farben, Spacing, Breakpoints anpassbar
- **Mixin System**: Einfache Erstellung neuer Responsive-Komponenten
- **CSS Override**: Standard CSS reicht aus für einfache Anpassungen
- **Theme-System**: Vordefinierte Themes leicht adaptierbar

#### Wartbarkeit
**Vorteile:**
- Große Community mit umfangreicher Dokumentation
- Konsistente Naming-Conventions
- Viele Online-Resources und Tutorials
- Einfache Integration in moderne Build-Tools (Webpack, Vite)
- Regelmäßige Updates und aktive Entwicklung

**Nachteile:**
- Lerningkurve für Bootstrap-Spezifiken
- Vendor Lock-in zur Bootstrap-Struktur
- Abhängigkeit von Boot JavaScript (für interactive Komponenten)

### 4. Konkrete Responsive-Betrachtung

#### Mobile-First Ansatz
Bootstrap unterstützt den Mobile-First Ansatz:
```html
<!-- Standard für mobile, dann für larger screens -->
<div class="col-12 col-md-6 col-lg-4">Content</div>
<!-- 100% Breite auf mobile, 50% ab md, 33% ab lg -->
```

#### Responsive Komponenten
- **Navigation**: Integriertes Navbar mit automatischem Collapse
- **Grid**: Flexibel anpassbar auf alle Bildschirmgrößen
- **Images**: Responsive Images mit img-fluid
- **Tables**: Scroll auf mobilen Geräten möglich
- **Forms**: Automatisch responsive auf allen Geräten

## Recommendation
**Bootstrap empfohlen** für folgende Gründe:

✅ **Responsive Design**: Ausgezeichnete Built-in Responsive Features
✅ **Performance**: Moderate Dateigröße, gute Optimierungsmöglichkeiten
✅ **Bundle-Größe**: Durch Custom Builds optimierbar
✅ **Maintainability**: Große Community, gute Dokumentation
✅ **Customization**: Umfangreiche Anpassungsmöglichkeiten via SASS

## Consequences
- Bootstrap v5+ (neueste stabile Version) einführen
- SASS Setup für Customization erforderlich
- Team-Training für Bootstrap-Conventions notwendig
- Schrittweise Migration bestehender Styles empfohlen
- Dokumentation von Custom Styles und Overrides pflegen