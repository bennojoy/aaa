import React, { useEffect, useCallback, useState, useRef } from 'react';
import { View, StyleSheet, FlatList, RefreshControl, TouchableOpacity, TextInput, Modal, ActivityIndicator } from 'react-native';
import { Text, Card, Button, Input, Overlay } from 'react-native-elements';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootState } from '../../store';
import { 
  searchRoomsRequest, 
  clearRoomError,
  createRoomRequest,
  addParticipantRequest
} from '../../store/roomSlice';
import { logger } from '../../utils/logger';
import { Room } from '../../types/room';
import { RootStackParamList } from '../../navigation/types';
import { logout } from '../../store/authSlice';
import { storage } from '../../utils/storage';
import { validateToken } from '../../utils/auth';
import { connect } from '../../store/mqttSlice';
import { apiClient } from '../../api/client';
import { getRoomUnreadCount, getLastUnreadMessage } from '../../store/selectors/chatSelectors';

type NavigationProp = NativeStackNavigationProp<RootStackParamList, 'Rooms'>;

/**
 * RoomsScreen Component
 * Displays a list of rooms the user has access to with search functionality
 */
export const RoomsScreen = () => {
  const dispatch = useDispatch();
  const navigation = useNavigation<NavigationProp>();
  const { rooms = [], loading, error, creatingRoom, addingParticipant } = useSelector((state: RootState) => state.rooms || { rooms: [], loading: false, error: null });
  const { connectionStatus, currentUserId } = useSelector((state: RootState) => state.mqtt);
  const { token } = useSelector((state: RootState) => state.auth);
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

  // Get unread counts and last unread message for all rooms
  const unreadCounts = useSelector((state: RootState) => 
    Object.fromEntries(rooms.map(room => [room.id, getRoomUnreadCount(room.id)(state)]))
  );
  const lastUnreadMessages = useSelector((state: RootState) => 
    Object.fromEntries(rooms.map(room => [room.id, getLastUnreadMessage(room.id)(state)]))
  );

  // Sort rooms based on unread messages
  const sortedRooms = React.useMemo(() => {
    return [...rooms].sort((a, b) => {
      const aUnread = unreadCounts[a.id] || 0;
      const bUnread = unreadCounts[b.id] || 0;
      if (aUnread > 0 && bUnread === 0) return -1;
      if (aUnread === 0 && bUnread > 0) return 1;
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    });
  }, [rooms, unreadCounts]);

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
    logger.info('Room selected', { roomId: room.id, roomType: 'user' }, 'room');
    navigation.navigate('Chat', {
      roomId: room.id,
      roomType: 'user',
      roomName: room.name
    });
  };

  const handleCreateRoom = () => {
    if (newRoomName.trim()) {
      dispatch(createRoomRequest({
        name: newRoomName.trim(),
        description: newRoomDescription.trim(),
        type: 'user'
      }));
      setShowCreateRoom(false);
      setNewRoomName('');
      setNewRoomDescription('');
    }
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
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Text style={styles.cardTitle}>{room.name}</Text>
            {unreadCount > 0 && (
              <View style={styles.unreadBadge}>
                <Text style={styles.unreadCount}>{unreadCount}</Text>
              </View>
            )}
          </View>
          <Text style={styles.description}>{room.description}</Text>
          {lastUnread && (
            <View style={styles.unreadPreview}>
              <Text style={styles.unreadPreviewText} numberOfLines={1}>
                {lastUnread.content}
              </Text>
              <Text style={styles.messageStatus}>
                {lastUnread.status === 'delivered' ? 'Delivered' : 
                 lastUnread.status === 'read' ? 'Read' : 
                 lastUnread.status === 'sent' ? 'Sent' : 
                 lastUnread.status === 'sending' ? 'Sending...' : 
                 lastUnread.status === 'failed' ? 'Failed' : lastUnread.status}
              </Text>
            </View>
          )}
          <View style={styles.cardFooter}>
            <Text style={styles.timestamp}>
              Created: {new Date(room.created_at).toLocaleDateString()}
            </Text>
            <TouchableOpacity 
              onPress={() => {
                setSelectedRoom(room);
                setShowAddParticipant(true);
              }}
              style={styles.addButton}
            >
              <Text style={styles.addButtonText}>Add Participant</Text>
            </TouchableOpacity>
          </View>
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.searchContainer}>
          <TextInput
            style={styles.searchInput}
            placeholder="Search rooms..."
            value={searchQuery}
            onChangeText={handleSearch}
            placeholderTextColor="#999"
          />
        </View>
        <Button
          title="Create Room"
          onPress={() => setShowCreateRoom(true)}
          buttonStyle={styles.createButton}
        />
      </View>

      {error && (
        <Text style={styles.error}>{error}</Text>
      )}

      <FlatList
        data={sortedRooms}
        renderItem={renderRoom}
        keyExtractor={(item) => `room-${item.id}`}
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

      {/* Create Room Modal */}
      <Overlay
        isVisible={showCreateRoom}
        onBackdropPress={() => setShowCreateRoom(false)}
        overlayStyle={styles.modal}
      >
        <Text h4 style={styles.modalTitle}>Create New Room</Text>
        <Input
          placeholder="Room Name"
          value={newRoomName}
          onChangeText={setNewRoomName}
          autoFocus
        />
        <Input
          placeholder="Description (optional)"
          value={newRoomDescription}
          onChangeText={setNewRoomDescription}
          multiline
        />
        <Button
          title="Create"
          onPress={handleCreateRoom}
          loading={creatingRoom}
          disabled={!newRoomName.trim() || creatingRoom}
        />
      </Overlay>

      {/* Add Participant Modal */}
      <Overlay
        isVisible={showAddParticipant}
        onBackdropPress={() => setShowAddParticipant(false)}
        overlayStyle={styles.modal}
      >
        <Text h4 style={styles.modalTitle}>Add Participant</Text>
        <Input
          placeholder="Search by name or phone number..."
          value={participantSearchQuery}
          onChangeText={handleParticipantSearch}
          autoFocus
        />
        {isSearching && (
          <ActivityIndicator size="small" color="#007AFF" style={styles.searchIndicator} />
        )}
        <FlatList
          data={searchResults}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={styles.userItem}
              onPress={() => handleParticipantSelect(item.id)}
            >
              <Text style={styles.userName}>{item.name || item.alias}</Text>
              <Text style={styles.userPhone}>{item.phone_number}</Text>
            </TouchableOpacity>
          )}
          style={styles.searchResults}
          ListEmptyComponent={
            !isSearching && participantSearchQuery.trim() ? (
              <Text style={styles.emptyText}>No users found</Text>
            ) : null
          }
        />
      </Overlay>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  searchContainer: {
    flex: 1,
    marginRight: 10,
  },
  searchInput: {
    backgroundColor: '#f5f5f5',
    borderRadius: 8,
    padding: 10,
    fontSize: 16,
  },
  createButton: {
    backgroundColor: '#007AFF',
    borderRadius: 8,
    paddingHorizontal: 15,
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
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
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
  addButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 5,
  },
  addButtonText: {
    color: '#fff',
    fontSize: 12,
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
  modal: {
    width: '90%',
    maxHeight: '80%',
    padding: 20,
    borderRadius: 10,
  },
  modalTitle: {
    marginBottom: 20,
    textAlign: 'center',
  },
  userItem: {
    padding: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  userName: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  userPhone: {
    fontSize: 14,
    color: '#666',
    marginTop: 5,
  },
  searchResults: {
    maxHeight: 200,
    marginTop: 10,
  },
  searchIndicator: {
    marginVertical: 10,
  },
  unreadBadge: {
    backgroundColor: '#007AFF',
    borderRadius: 12,
    minWidth: 24,
    height: 24,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 8,
  },
  unreadCount: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  unreadPreview: {
    backgroundColor: '#f0f0f0',
    padding: 8,
    borderRadius: 4,
    marginVertical: 8,
  },
  unreadPreviewText: {
    fontSize: 14,
    color: '#666',
  },
  messageStatus: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
    fontStyle: 'italic'
  },
}); 