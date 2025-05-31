import { createSelector } from '@reduxjs/toolkit';
import { RootState } from '../store/store';
import { Room } from '../../types/room';
import { getRoomUnreadCount, getLastUnreadMessage } from './chatSelectors';

const initialState = {
  rooms: [],
  total: 0,
  loading: false,
  error: null,
  creatingRoom: false,
  addingParticipant: false
};

export const selectRoomState = (state: RootState) => {
  if (!state || !state.rooms) {
    return initialState;
  }
  return state.rooms;
};

export const selectRooms = createSelector(
  selectRoomState,
  (roomState) => {
    if (!roomState || !Array.isArray(roomState.rooms)) {
      return [];
    }
    return roomState.rooms;
  }
);

export const selectRoomLoading = createSelector(
  selectRoomState,
  (roomState) => roomState?.loading || false
);

export const selectRoomError = createSelector(
  selectRoomState,
  (roomState) => roomState?.error || null
);

export const selectRoomTotal = createSelector(
  selectRoomState,
  (roomState) => roomState?.total || 0
);

export const selectCreatingRoom = createSelector(
  selectRoomState,
  (roomState) => roomState?.creatingRoom || false
);

export const selectAddingParticipant = createSelector(
  selectRoomState,
  (roomState) => roomState?.addingParticipant || false
);

// Memoized selectors for unread counts and last unread messages
export const selectUnreadCounts = createSelector(
  [selectRooms, (state: RootState) => state],
  (rooms, state) => {
    if (!Array.isArray(rooms)) {
      return {};
    }
    return Object.fromEntries(
      rooms.map((room: Room) => [room.id, getRoomUnreadCount(room.id)(state)])
    );
  }
);

export const selectLastUnreadMessages = createSelector(
  [selectRooms, (state: RootState) => state],
  (rooms, state) => {
    if (!Array.isArray(rooms)) {
      return {};
    }
    return Object.fromEntries(
      rooms.map((room: Room) => [room.id, getLastUnreadMessage(room.id)(state)])
    );
  }
); 