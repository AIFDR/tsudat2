<?xml version="1.0" encoding="ISO-8859-1"?>
<StyledLayerDescriptor version="1.0.0" 
    xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd" 
    xmlns="http://www.opengis.net/sld" 
    xmlns:ogc="http://www.opengis.net/ogc" 
    xmlns:xlink="http://www.w3.org/1999/xlink" 
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <NamedLayer>
        <Name>tsudat_hazardpoint_rp</Name>
        <UserStyle>
            <Title>TsuDAT Hazard Point for Return Period Style</Title>
            <Abstract>Style for layer tsudat_hazardpoint_rp</Abstract>
            <FeatureTypeStyle>
                <Rule>
                    <MinScaleDenominator>500000</MinScaleDenominator>
                    <PointSymbolizer>
                        <Graphic>
                            <Mark>
                                <WellKnownName>square</WellKnownName>
                                <Fill>
                                    <CssParameter name="fill">#0000ff</CssParameter>
                                </Fill>
                            </Mark>
                            <Size>6</Size>
                            <Rotation>45</Rotation>
                        </Graphic>
                    </PointSymbolizer>
                </Rule>
                <Rule>
                    <MaxScaleDenominator>500000</MaxScaleDenominator>
                    <PointSymbolizer>
                        <Graphic>
                            <Mark>
                                <WellKnownName>square</WellKnownName>
                                <Fill>
                                    <CssParameter name="fill">#0000ff</CssParameter>
                                </Fill>
                            </Mark>
                            <Size>12</Size>
                            <Rotation>45</Rotation>
                        </Graphic>
                    </PointSymbolizer>
                </Rule>
            </FeatureTypeStyle>
        </UserStyle>
    </NamedLayer>
</StyledLayerDescriptor>
