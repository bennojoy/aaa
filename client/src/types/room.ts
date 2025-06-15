/**
 * Represents a chat room in the application
 */
export interface Room {
  /** Unique identifier for the room */
  id: string;
  /** Name of the room */
  name: string;
  /** Description of the room */
  description: string;
  /** Type of the room */
  type: 'user' | 'assistant';
  /** ISO timestamp when the room was created */
  created_at: string;
  /** ISO timestamp when the room was last updated */
  updated_at: string | null;
  /** ID of the user who created the room */
  created_by: string;
  /** Whether this is a default room */
  is_default: boolean;
  /** Name of the assistant in the room */
  assistant_name: string;
  /** List of participants in the room */
  participants?: Array<{
    /** User ID */
    id: string;
    /** User's name */
    name: string;
    /** User's role in the room */
    role: 'member' | 'admin';
    /** User's status in the room */
    status: 'ACTIVE' | 'INACTIVE' | 'BANNED';
  }>;
}

/**
 * Response from the rooms API containing a list of rooms and pagination info
 */
export interface RoomList {
  /** Array of room objects */
  rooms: Room[];
  /** Total number of rooms matching the query */
  total: number;
  /** Optional trace ID for request tracking */
  trace_id?: string;
}

/**
 * Parameters for searching rooms
 */
export interface RoomSearchParams {
  /** Optional search query to filter rooms by name */
  query?: string;
  /** Number of rooms to skip (for pagination) */
  skip?: number;
  /** Maximum number of rooms to return */
  limit?: number;
}

/**
 * Parameters for creating a new room
 */
export interface CreateRoomParams {
  /** Name of the room */
  name: string;
  /** Description of the room */
  description?: string;
  /** Type of the room */
  type: 'user' | 'assistant';
}

/**
 * Parameters for searching users
 */
export interface UserSearchParams {
  /** Search query to filter users */
  query: string;
}

/**
 * User search result
 */
export interface UserSearchResult {
  /** Array of user objects */
  users: Array<{
    /** User ID */
    id: string;
    /** User's name */
    name: string;
    /** User's phone number */
    phone_number: string;
    /** User's status */
    status: string;
  }>;
}

/**
 * Parameters for adding a participant to a room
 */
export interface AddParticipantParams {
  /** Room ID */
  roomId: string;
  /** User ID to add */
  userId: string;
  /** Role of the participant (optional) */
  role?: 'member' | 'admin';
  /** Status of the participant (optional) */
  status?: 'ACTIVE';
} 