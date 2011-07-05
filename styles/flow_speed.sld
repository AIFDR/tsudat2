<?xml version="1.0" encoding="UTF-8"?>
<sld:StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:sld="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:gml="http://www.opengis.net/gml" version="1.0.0">
  <sld:NamedLayer>
    <sld:Name>flow_speed</sld:Name>
    <sld:UserStyle>
      <sld:Name>flow_speed</sld:Name>
      <sld:Title>tsunami_flow_speed</sld:Title>
      <sld:IsDefault>1</sld:IsDefault>
      <sld:FeatureTypeStyle>
        <sld:Name>name</sld:Name>
        <sld:Rule>
          <sld:RasterSymbolizer>
            <sld:Geometry>
              <ogc:PropertyName>geom</ogc:PropertyName>
            </sld:Geometry>
            <sld:ColorMap>
              <sld:ColorMapEntry color="#000000" opacity="0" quantity="0"/>
              <sld:ColorMapEntry color="#5571CF" opacity="1" quantity="0.5"/>
              <sld:ColorMapEntry color="#000000" opacity="1" quantity="1"/>
              <sld:ColorMapEntry color="#8B97CC" opacity="1" quantity="1.5"/>
              <sld:ColorMapEntry color="#A7AEC9" opacity="1" quantity="2"/>
              <sld:ColorMapEntry color="#BFC3C7" opacity="1" quantity="2.5"/>
              <sld:ColorMapEntry color="#DADBC5" opacity="1" quantity="3"/>
              <sld:ColorMapEntry color="#F2F2BF" opacity="1" quantity="3.5"/>
              <sld:ColorMapEntry color="#FCF0B3" opacity="1" quantity="4"/>
              <sld:ColorMapEntry color="#F7D59E" opacity="1" quantity="4.5"/>
              <sld:ColorMapEntry color="#F0BC8B" opacity="1" quantity="5"/>
              <sld:ColorMapEntry color="#EBA57A" opacity="1" quantity="6"/>
              <sld:ColorMapEntry color="#E08865" opacity="1" quantity="7"/>
              <sld:ColorMapEntry color="#D97357" opacity="1" quantity="8"/>
              <sld:ColorMapEntry color="#CF5B46" opacity="1" quantity="9"/>
              <sld:ColorMapEntry color="#C44539" opacity="1" quantity="10"/>
            </sld:ColorMap>
          </sld:RasterSymbolizer>
        </sld:Rule>
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:NamedLayer>
</sld:StyledLayerDescriptor>

