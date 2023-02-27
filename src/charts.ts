import * as d3 from 'd3';

export function makeLineChart(
  node: SVGSVGElement | null | undefined,
  data: Array<[number, number]>,
  xRange?: [number, number],
  yRange?: [number, number],
  width?: number,
  height?: number
): SVGSVGElement {
  const svg = node
    ? d3.select<SVGSVGElement, undefined>(node)
    : d3.create('svg');
  width =
    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
    width === undefined || width === null ? svg.node()!.clientWidth : width;
  height =
    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
    height === undefined || height === null ? svg.node()!.clientHeight : height;
  if (height > 16) {
    height -= 4;
  }
  if (!xRange) {
    const xData = data.map((d) => d[0]);
    xRange = [Math.min(...xData), Math.max(...xData)];
  }
  if (xRange[0] === xRange[1]) {
    xRange[1] += 1;
  }
  if (!yRange) {
    const yData = data.map((d) => d[1]);
    yRange = [Math.min(...yData), Math.max(...yData)];
  }
  if (yRange[0] === yRange[1]) {
    yRange[1] += 1;
  }
  const xOffset = -xRange[0];
  const xScale = width / (xRange[1] - xRange[0]);
  const yOffset = -yRange[0];
  const yScale = height / (yRange[1] - yRange[0]);
  const lineFunc = d3
    .line()
    .x((d) => (d[0] + xOffset) * xScale)
    .y((d) => (d[1] + yOffset) * yScale);
  let path = svg.select<SVGPathElement>('path');
  if (path.size() === 0) {
    path = svg.append('path').attr('fill', 'none');
  }
  path.attr('d', lineFunc(data));
  // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
  return svg.node()!;
}
