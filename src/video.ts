const svgNS = 'http://www.w3.org/2000/svg';

export function createSymbol(
  id: string,
  pathD: string,
  viewBox = '0 0 24 24'
): SVGSymbolElement {
  const symbol = document.createElementNS(svgNS, 'symbol');
  symbol.id = id;
  symbol.setAttribute('viewBox', viewBox);
  const path = document.createElementNS(svgNS, 'path');
  path.setAttribute('d', pathD);
  symbol.appendChild(path);
  return symbol;
}

export function createControlsSvg(): SVGSVGElement {
  const svg = document.createElementNS(svgNS, 'svg');
  const defs = document.createElementNS(svgNS, 'defs');
  svg.appendChild(defs);
  defs.appendChild(
    createSymbol(
      'pause',
      'M14.016 5.016h3.984v13.969h-3.984v-13.969zM6 18.984v-13.969h3.984v13.969h-3.984z'
    )
  );
  defs.appendChild(
    createSymbol('play-icon', 'M8.016 5.016l10.969 6.984-10.969 6.984v-13.969z')
  );
  defs.appendChild(
    createSymbol(
      'volume-high',
      'M14.016 3.234q3.047 0.656 5.016 3.117t1.969 5.648-1.969 5.648-5.016 3.117v-2.063q2.203-0.656 3.586-2.484t1.383-4.219-1.383-4.219-3.586-2.484v-2.063zM16.5 12q0 2.813-2.484 4.031v-8.063q1.031 0.516 1.758 1.688t0.727 2.344zM3 9h3.984l5.016-5.016v16.031l-5.016-5.016h-3.984v-6z'
    )
  );
  defs.appendChild(
    createSymbol(
      'volume-low',
      'M5.016 9h3.984l5.016-5.016v16.031l-5.016-5.016h-3.984v-6zM18.516 12q0 2.766-2.531 4.031v-8.063q1.031 0.516 1.781 1.711t0.75 2.32z'
    )
  );
  defs.appendChild(
    createSymbol(
      'volume-mute',
      'M12 3.984v4.219l-2.109-2.109zM4.266 3l16.734 16.734-1.266 1.266-2.063-2.063q-1.547 1.313-3.656 1.828v-2.063q1.172-0.328 2.25-1.172l-4.266-4.266v6.75l-5.016-5.016h-3.984v-6h4.734l-4.734-4.734zM18.984 12q0-2.391-1.383-4.219t-3.586-2.484v-2.063q3.047 0.656 5.016 3.117t1.969 5.648q0 2.203-1.031 4.172l-1.5-1.547q0.516-1.266 0.516-2.625zM16.5 12q0 0.422-0.047 0.609l-2.438-2.438v-2.203q1.031 0.516 1.758 1.688t0.727 2.344z'
    )
  );
  defs.appendChild(
    createSymbol(
      'fullscreen',
      'M14.016 5.016h4.969v4.969h-1.969v-3h-3v-1.969zM17.016 17.016v-3h1.969v4.969h-4.969v-1.969h3zM5.016 9.984v-4.969h4.969v1.969h-3v3h-1.969zM6.984 14.016v3h3v1.969h-4.969v-4.969h1.969z'
    )
  );
  defs.appendChild(
    createSymbol(
      'fullscreen-exit',
      'M15.984 8.016h3v1.969h-4.969v-4.969h1.969v3zM14.016 18.984v-4.969h4.969v1.969h-3v3h-1.969zM8.016 8.016v-3h1.969v4.969h-4.969v-1.969h3zM5.016 15.984v-1.969h4.969v4.969h-1.969v-3h-3z'
    )
  );
  defs.appendChild(
    createSymbol(
      'pip',
      'M21 19.031v-14.063h-18v14.063h18zM23.016 18.984q0 0.797-0.609 1.406t-1.406 0.609h-18q-0.797 0-1.406-0.609t-0.609-1.406v-14.016q0-0.797 0.609-1.383t1.406-0.586h18q0.797 0 1.406 0.586t0.609 1.383v14.016zM18.984 11.016v6h-7.969v-6h7.969z'
    )
  );
  return svg;
}
