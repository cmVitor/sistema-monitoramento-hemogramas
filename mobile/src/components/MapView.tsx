import React, { useEffect, useState } from 'react';
import {
  StyleSheet,
  View,
  Text,
  ActivityIndicator,
  Alert,
} from 'react-native';
import MapView, { Marker, Circle, PROVIDER_GOOGLE } from 'react-native-maps';
import { locationService } from '../services/locationService';
import { apiService, OutbreakRegion } from '../services/api';

interface MapScreenProps {
  currentLocation?: {
    latitude: number;
    longitude: number;
  } | null;
  inOutbreakZone?: boolean;
}

export default function MapScreen({ currentLocation, inOutbreakZone }: MapScreenProps) {
  const [userLocation, setUserLocation] = useState(currentLocation);
  const [outbreakData, setOutbreakData] = useState<OutbreakRegion | null>(null);
  const [loading, setLoading] = useState(true);
  const [region, setRegion] = useState({
    latitude: currentLocation?.latitude || -23.5505,
    longitude: currentLocation?.longitude || -46.6333,
    latitudeDelta: 0.05,
    longitudeDelta: 0.05,
  });

  useEffect(() => {
    initializeMap();
    const interval = setInterval(fetchOutbreakData, 10 * 60 * 1000); // Atualizar a cada 10 minutos
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (currentLocation) {
      setUserLocation(currentLocation);
      setRegion({
        latitude: currentLocation.latitude,
        longitude: currentLocation.longitude,
        latitudeDelta: 0.05,
        longitudeDelta: 0.05,
      });
    }
  }, [currentLocation]);

  const initializeMap = async () => {
    try {
      setLoading(true);

      // Obter localização atual se não fornecida
      if (!userLocation) {
        const hasPermissions = await locationService.hasPermissions();
        if (hasPermissions) {
          const location = await locationService.getCurrentLocation();
          const coords = {
            latitude: location.coords.latitude,
            longitude: location.coords.longitude,
          };
          setUserLocation(coords);
          setRegion({
            ...coords,
            latitudeDelta: 0.05,
            longitudeDelta: 0.05,
          });
        }
      }

      // Buscar dados de surto
      await fetchOutbreakData();
    } catch (error) {
      console.error('Erro ao inicializar mapa:', error);
      Alert.alert('Erro', 'Não foi possível carregar o mapa');
    } finally {
      setLoading(false);
    }
  };

  const fetchOutbreakData = async () => {
    try {
      const data = await apiService.getOutbreakRegions();
      setOutbreakData(data);
      console.log('Dados de surto atualizados:', data);
    } catch (error) {
      console.error('Erro ao buscar dados de surto:', error);
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#FF6B6B" />
        <Text style={styles.loadingText}>Carregando mapa...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <MapView
        provider={PROVIDER_GOOGLE}
        style={styles.map}
        region={region}
        showsUserLocation
        showsMyLocationButton
        showsCompass
      >
        {/* Marcador da localização do usuário */}
        {userLocation && (
          <Marker
            coordinate={userLocation}
            title="Você está aqui"
            description={inOutbreakZone ? '⚠️ Você está em zona de surto!' : 'Sua localização atual'}
            pinColor={inOutbreakZone ? '#FF0000' : '#4CAF50'}
          />
        )}

        {/* Círculo da zona de surto */}
        {outbreakData && (
          <>
            <Circle
              center={{
                latitude: outbreakData.centroid.lat,
                longitude: outbreakData.centroid.lng,
              }}
              radius={outbreakData.radius}
              fillColor="rgba(124, 45, 18, 0.15)"
              strokeColor="#fbbf24"
              strokeWidth={3}
            />
            <Marker
              coordinate={{
                latitude: outbreakData.centroid.lat,
                longitude: outbreakData.centroid.lng,
              }}
              title="⚠️ Zona de Surto"
              description={`${outbreakData.point_count} casos detectados`}
              pinColor="#7c2d12"
            />
          </>
        )}
      </MapView>

      {/* Banner informativo */}
      {outbreakData && (
        <View style={styles.infoBanner}>
          <Text style={styles.infoBannerTitle}>⚠️ Zona de Surto Detectada</Text>
          <Text style={styles.infoBannerText}>
            {outbreakData.point_count} casos na região
          </Text>
          {inOutbreakZone && (
            <Text style={styles.infoBannerWarning}>
              Você está dentro da zona de surto!
            </Text>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  map: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666',
  },
  infoBanner: {
    position: 'absolute',
    top: 10,
    left: 10,
    right: 10,
    backgroundColor: 'rgba(124, 45, 18, 0.95)',
    borderRadius: 12,
    padding: 15,
    borderWidth: 2,
    borderColor: '#fbbf24',
  },
  infoBannerTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 5,
  },
  infoBannerText: {
    fontSize: 14,
    color: '#fff',
  },
  infoBannerWarning: {
    fontSize: 13,
    color: '#fbbf24',
    fontWeight: 'bold',
    marginTop: 5,
  },
});
