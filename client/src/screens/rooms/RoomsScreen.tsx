import React, { useEffect, useCallback } from 'react';
import { View, StyleSheet, FlatList, RefreshControl, TouchableOpacity, TextInput } from 'react-native';
import { Text, Card, Button } from 'react-native-elements';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootState } from '../../store';
import { searchRoomsRequest, clearRoomError } from '../../store/roomSlice';
import { logger } from '../../utils/logger';
import { Room } from '../../types/room';
import { RootStackParamList } from '../../navigation/types';
import { logout } from '../../store/authSlice';
import { storage } from '../../utils/storage';
import { validateToken } from '../../utils/auth';
import { connect } from '../../store/mqttSlice';

type NavigationProp = NativeStackNavigationProp<RootStackParamList, 'Rooms'>;

/**
 * RoomsScreen Component
 * Displays a list of rooms the user has access to with search functionality
 */
export const RoomsScreen = () => {
  const dispatch = useDispatch();
  const navigation = useNavigation<NavigationProp>();
  const { rooms = [], loading, error } = useSelector((state: RootState) => state.rooms || { rooms: [], loading: false, error: null });
  const { connectionStatus, currentUserId } = useSelector((state: RootState) => state.mqtt);
  const { token } = useSelector((state: RootState) => state.auth);
  const [searchQuery, setSearchQuery] = React.useState('');

  useEffect(() => {
    logger.info('Rooms screen mounted', null, 'room');
    validateTokenAndLoadRooms();
    return () => {
      logger.info('Rooms screen unmounted', null, 'room');
      dispatch(clearRoomError());
    };
  }, [dispatch]);

  // Handle MQTT reconnection when screen comes into focus
  useFocusEffect(
    useCallback(() => {
      const reconnectMQTT = async () => {
        if (connectionStatus === 'disconnected' && currentUserId && token) {
          logger.info('Attempting MQTT reconnection on screen focus', {
            userId: currentUserId,
            hasToken: !!token
          }, 'mqtt');
          
          dispatch(connect({ token, userId: currentUserId }));
        }
      };

      reconnectMQTT();
    }, [connectionStatus, currentUserId, token, dispatch])
  );

  /**
   * Validates token and loads rooms if valid
   */
  const validateTokenAndLoadRooms = async () => {
    try {
      const isValid = await validateToken();
      if (!isValid) {
        logger.error('Token validation failed', null, 'auth');
        handleLogout();
        return;
      }

      // Load rooms when component mounts
      dispatch(searchRoomsRequest({}));
    } catch (error) {
      logger.error('Token validation failed', { error }, 'auth');
      handleLogout();
    }
  };

  /**
   * Handles logout when token is invalid
   */
  const handleLogout = async () => {
    try {
      await storage.clear();
      dispatch(logout());
      navigation.reset({
        index: 0,
        routes: [{ name: 'Login' }],
      });
    } catch (error) {
      logger.error('Logout failed', { error }, 'auth');
    }
  };

  /**
   * Handles search input changes
   * @param query - The search query string
   */
  const handleSearch = (query: string) => {
    logger.debug('Search query changed', { query }, 'room');
    setSearchQuery(query);
    dispatch(searchRoomsRequest({ query }));
  };

  /**
   * Handles pull-to-refresh action
   */
  const handleRefresh = () => {
    logger.debug('Refreshing rooms list', { query: searchQuery }, 'room');
    dispatch(searchRoomsRequest({ query: searchQuery }));
  };

  /**
   * Handles room selection
   * @param room - The selected room
   */
  const handleRoomSelect = (room: Room) => {
    logger.info('Room selected', { roomId: room.id, roomType: 'assistant' }, 'room');
    navigation.navigate('Chat', {
      roomId: room.id,
      roomType: 'assistant',
      roomName: room.name
    });
  };

  /**
   * Renders a single room card
   * @param param0 - The room item to render
   */
  const renderRoom = ({ item: room }: { item: Room }) => (
    <TouchableOpacity onPress={() => handleRoomSelect(room)}>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>{room.name}</Text>
        <Text style={styles.description}>{room.description}</Text>
        <View style={styles.cardFooter}>
          <Text style={styles.timestamp}>
            Created: {new Date(room.created_at).toLocaleDateString()}
          </Text>
        </View>
      </View>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <View style={styles.searchContainer}>
        <TextInput
          style={styles.searchInput}
          placeholder="Search rooms..."
          value={searchQuery}
          onChangeText={handleSearch}
          placeholderTextColor="#999"
        />
      </View>

      {error && (
        <Text style={styles.error}>{error}</Text>
      )}

      <FlatList
        data={rooms}
        renderItem={renderRoom}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl
            refreshing={loading}
            onRefresh={handleRefresh}
          />
        }
        ListEmptyComponent={
          !loading ? (
            <Text style={styles.emptyText}>
              No rooms found. Create a new room to get started!
            </Text>
          ) : null
        }
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  searchContainer: {
    backgroundColor: '#fff',
    padding: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  searchInput: {
    backgroundColor: '#f5f5f5',
    borderRadius: 8,
    padding: 10,
    fontSize: 16,
  },
  list: {
    padding: 10,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 8,
    marginBottom: 10,
    padding: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  description: {
    marginBottom: 10,
    color: '#666',
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 10,
  },
  timestamp: {
    fontSize: 12,
    color: '#999',
  },
  error: {
    color: 'red',
    textAlign: 'center',
    margin: 10,
  },
  emptyText: {
    textAlign: 'center',
    color: '#666',
    marginTop: 20,
  },
}); 