import React, { useEffect, useCallback, useState, useRef } from 'react';
import { View, FlatList, RefreshControl, TouchableOpacity, TextInput, Modal, ActivityIndicator, StyleSheet } from 'react-native';
import { Text } from 'react-native-elements';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootState } from '../../store/store';
import {
  searchRoomsRequest,
  searchRoomsSuccess,
  searchRoomsFailure,
  createRoomRequest,
  createRoomSuccess,
  createRoomFailure,
  clearRoomError,
  addParticipantRequest
} from '../../store/slices/roomSlice';
import { logger } from '../../utils/logger';
import { Room } from '../../types/room';
import { RootStackParamList } from '../../navigation/types';
import { logout } from '../../store/slices/authSlice';
import { storage } from '../../utils/storage';
import { validateToken } from '../../utils/auth';
import { connect as connectMQTT } from '../../store/slices/mqttSlice';
import { apiClient } from '../../api/client';
import { getRoomUnreadCount, getLastUnreadMessage } from '../../store/selectors/chatSelectors';
import { getTraceId } from '../../utils/trace';
import { loginRequest } from '../../store/slices/authSlice';
import {
  selectRooms,
  selectRoomLoading,
  selectRoomError,
  selectCreatingRoom,
  selectAddingParticipant,
  selectUnreadCounts,
  selectLastUnreadMessages
} from '../../store/selectors/roomSelectors';

type NavigationProp = NativeStackNavigationProp<RootStackParamList, 'Rooms'>;

interface AuthState {
  token: string | null;
  user: {
    id: string;
    name: string;
  } | null;
}

/**
 * RoomsScreen Component
 * Displays a list of rooms the user has access to with search functionality
 */
export const RoomsScreen = () => {
  const dispatch = useDispatch();
  const navigation = useNavigation<NavigationProp>();
  
  // Use selectors with default values
  const rooms = useSelector(selectRooms) || [];
  const loading = useSelector(selectRoomLoading) || false;
  const error = useSelector(selectRoomError) || null;
  const creatingRoom = useSelector(selectCreatingRoom) || false;
  const addingParticipant = useSelector(selectAddingParticipant) || false;
  
  const { connectionStatus, currentUserId } = useSelector((state: RootState) => state.mqtt);
  const { token, user } = useSelector((state: RootState & { auth: AuthState }) => state.auth);
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateRoom, setShowCreateRoom] = useState(false);
  const [showAddParticipant, setShowAddParticipant] = useState(false);
  const [selectedRoom, setSelectedRoom] = useState<Room | null>(null);
  const [newRoomName, setNewRoomName] = useState('');
  const [newRoomDescription, setNewRoomDescription] = useState('');
  const [participantSearchQuery, setParticipantSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const searchTimeoutRef = useRef<NodeJS.Timeout>();

  const unreadCounts = useSelector(selectUnreadCounts);
  const lastUnreadMessages = useSelector(selectLastUnreadMessages);

  console.log('RoomsScreen state:', {
    rooms,
    loading,
    error,
    creatingRoom,
    addingParticipant,
    unreadCounts,
    lastUnreadMessages,
    mqtt: { connectionStatus, currentUserId },
    auth: { token: !!token, user }
  });

  // Sort rooms based on unread messages and ensure uniqueness
  const sortedRooms = React.useMemo(() => {
    console.log('Computing sortedRooms:', { inputRooms: rooms, unreadCounts });

    // First deduplicate rooms by ID
    const uniqueRooms = rooms.reduce((acc: Room[], room: Room) => {
      if (!acc.find(r => r.id === room.id)) {
        acc.push(room);
      }
      return acc;
    }, []);

    console.log('Unique rooms:', uniqueRooms);

    // Then sort the unique rooms
    const sorted = uniqueRooms.sort((a: Room, b: Room) => {
      const aUnread = unreadCounts[a.id] || 0;
      const bUnread = unreadCounts[b.id] || 0;
      if (aUnread > 0 && bUnread === 0) return -1;
      if (aUnread === 0 && bUnread > 0) return 1;
      
      // Handle null updated_at values by using created_at as fallback
      const aDate = a.updated_at ? new Date(a.updated_at) : new Date(a.created_at);
      const bDate = b.updated_at ? new Date(b.updated_at) : new Date(b.created_at);
      return bDate.getTime() - aDate.getTime();
    });

    console.log('Sorted rooms:', sorted);

    return sorted;
  }, [rooms, unreadCounts]);

  useEffect(() => {
    const traceId = getTraceId();
    logger.info('Rooms screen mounted', { traceId }, 'room');
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
          
          dispatch(connectMQTT({ token, userId: currentUserId }));
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
      dispatch(searchRoomsRequest({ query: '' }));
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
    logger.info('Room selected', { roomId: room.id, roomType: room.type }, 'room');
    navigation.navigate('Chat', {
      roomId: room.id,
      roomType: room.type,
      roomName: room.name
    });
  };

  const handleCreateRoom = () => {
    if (!user?.id) {
      logger.error('Cannot create room: No user ID', null, 'room');
      return;
    }

    const roomName = `Room ${rooms.length + 1}`;
    dispatch(createRoomRequest({
      name: roomName,
      description: 'Created from mobile app',
      type: 'user'
    }));
  };

  const handleAddParticipant = async () => {
    if (selectedRoom && participantSearchQuery.trim()) {
      try {
        setIsSearching(true);
        const response = await apiClient.get('/api/v1/rooms/users/search', {
          params: { 
            query: participantSearchQuery.trim(),
            exclude_room_id: selectedRoom.id // Exclude users already in the room
          }
        });
        setSearchResults(response.data.users || []);
      } catch (error: any) {
        logger.error('Failed to search users', { error: error.message }, 'room');
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }
  };

  const handleParticipantSearch = (query: string) => {
    setParticipantSearchQuery(query);
    
    // Clear previous timeout
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    
    // Set new timeout for search
    searchTimeoutRef.current = setTimeout(() => {
      if (query.trim()) {
        handleAddParticipant();
      } else {
        setSearchResults([]);
      }
    }, 300); // 300ms debounce
  };

  const handleParticipantSelect = (userId: string) => {
    if (selectedRoom) {
      dispatch(addParticipantRequest({
        roomId: selectedRoom.id,
        userId,
        role: 'member'
      }));
      setShowAddParticipant(false);
      setParticipantSearchQuery('');
      setSearchResults([]);
    }
  };

  /**
   * Renders a single room card
   * @param param0 - The room item to render
   */
  const renderRoom = ({ item: room }: { item: Room }) => {
    const unreadCount = unreadCounts[room.id] || 0;
    const lastUnread = lastUnreadMessages[room.id];

    return (
      <TouchableOpacity onPress={() => handleRoomSelect(room)}>
        <View className="bg-white p-4 mb-2 rounded-lg shadow-sm">
          <View className="flex-row justify-between items-center">
            <Text className="text-lg font-semibold text-foreground">{room.name}</Text>
            {unreadCount > 0 && (
              <View className="bg-primary rounded-full px-2 py-1">
                <Text className="text-white text-sm">{unreadCount}</Text>
              </View>
            )}
          </View>
          {lastUnread && (
            <Text className="text-grey-2 mt-1" numberOfLines={1}>
              {lastUnread.content}
            </Text>
          )}
        </View>
      </TouchableOpacity>
    );
  };

  const renderEmptyList = () => {
    if (!loading) {
      return (
        <Text className="text-grey-2 text-center mt-8">
          No rooms found
        </Text>
      );
    }
    return null;
  };

  const renderSearchEmptyList = () => {
    if (participantSearchQuery.trim()) {
      return (
        <Text className="text-grey-2 text-center py-4">
          No users found
        </Text>
      );
    }
    return null;
  };

  return (
    <View style={styles.container}>
      <View style={styles.searchContainer}>
        <TextInput
          style={styles.searchInput}
          placeholder="Search rooms..."
          placeholderTextColor="#86939e"
          value={searchQuery}
          onChangeText={handleSearch}
        />
      </View>

      {error && (
        <Text style={styles.errorText}>{error}</Text>
      )}

      <FlatList
        data={sortedRooms}
        renderItem={renderRoom}
        keyExtractor={item => item.id}
        refreshControl={
          <RefreshControl
            refreshing={loading}
            onRefresh={handleRefresh}
            colors={['#007AFF']}
          />
        }
        contentContainerStyle={styles.roomList}
        ListEmptyComponent={renderEmptyList}
      />

      <TouchableOpacity
        style={[styles.createButton, creatingRoom && styles.createButtonDisabled]}
        onPress={handleCreateRoom}
        disabled={creatingRoom}
      >
        <Text style={styles.createButtonText}>
          {creatingRoom ? 'Creating...' : 'Create Room'}
        </Text>
      </TouchableOpacity>

      <Modal
        visible={showCreateRoom}
        transparent
        animationType="fade"
        onRequestClose={() => setShowCreateRoom(false)}
      >
        <View className="flex-1 bg-black/50 justify-center items-center">
          <View className="bg-white w-11/12 rounded-lg p-6">
            <Text className="text-xl font-bold mb-4 text-foreground">Create New Room</Text>
            
            <TextInput
              className="bg-grey-5 px-4 py-3 rounded-lg text-foreground mb-4"
              placeholder="Room Name"
              placeholderTextColor="#86939e"
              value={newRoomName}
              onChangeText={setNewRoomName}
            />

            <TextInput
              className="bg-grey-5 px-4 py-3 rounded-lg text-foreground mb-6"
              placeholder="Description (optional)"
              placeholderTextColor="#86939e"
              value={newRoomDescription}
              onChangeText={setNewRoomDescription}
              multiline
            />

            <View className="flex-row justify-end space-x-4">
              <TouchableOpacity
                className="px-6 py-2"
                onPress={() => setShowCreateRoom(false)}
              >
                <Text className="text-grey-2">Cancel</Text>
              </TouchableOpacity>

              <TouchableOpacity
                className={`bg-primary px-6 py-2 rounded-lg ${!newRoomName.trim() ? 'opacity-50' : ''}`}
                onPress={handleCreateRoom}
                disabled={!newRoomName.trim() || creatingRoom}
              >
                <Text className="text-white font-semibold">
                  {creatingRoom ? 'Creating...' : 'Create'}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      <Modal
        visible={showAddParticipant}
        transparent
        animationType="fade"
        onRequestClose={() => setShowAddParticipant(false)}
      >
        <View className="flex-1 bg-black/50 justify-center items-center">
          <View className="bg-white w-11/12 rounded-lg p-6">
            <Text className="text-xl font-bold mb-4 text-foreground">Add Participant</Text>
            
            <TextInput
              className="bg-grey-5 px-4 py-3 rounded-lg text-foreground mb-4"
              placeholder="Search users..."
              placeholderTextColor="#86939e"
              value={participantSearchQuery}
              onChangeText={handleParticipantSearch}
            />

            {isSearching ? (
              <ActivityIndicator color="#007AFF" />
            ) : (
              <FlatList
                data={searchResults}
                keyExtractor={item => item.id}
                renderItem={({ item }) => (
                  <TouchableOpacity
                    className="py-3 border-b border-grey-5"
                    onPress={() => handleParticipantSelect(item.id)}
                  >
                    <Text className="text-foreground">{item.name}</Text>
                  </TouchableOpacity>
                )}
                ListEmptyComponent={renderSearchEmptyList}
              />
            )}

            <TouchableOpacity
              className="mt-4 bg-grey-5 px-6 py-2 rounded-lg"
              onPress={() => setShowAddParticipant(false)}
            >
              <Text className="text-foreground text-center">Close</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  searchContainer: {
    padding: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  searchInput: {
    backgroundColor: '#f5f5f5',
    padding: 12,
    borderRadius: 8,
    fontSize: 16,
  },
  roomList: {
    padding: 16,
  },
  roomItem: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 8,
    marginBottom: 8,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 1,
    },
    shadowOpacity: 0.2,
    shadowRadius: 1.41,
    elevation: 2,
  },
  roomName: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 4,
  },
  roomDescription: {
    fontSize: 14,
    color: '#666',
  },
  errorText: {
    color: '#ff3b30',
    textAlign: 'center',
    margin: 16,
  },
  emptyText: {
    textAlign: 'center',
    color: '#666',
    marginTop: 32,
  },
  createButton: {
    backgroundColor: '#007AFF',
    margin: 16,
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  createButtonDisabled: {
    opacity: 0.5,
  },
  createButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
}); 