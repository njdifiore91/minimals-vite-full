package com.dollarfunding.mca.security;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * Spring Data JPA repository interface for User entities.
 * Provides database access methods for user information.
 * 
 * This repository is essential for user authentication and management,
 * supporting the JWT authentication system integrated with Minimal UI Kit.
 */
@Repository
public interface UserRepository extends JpaRepository<User, Long> {
    
    /**
     * Find a user by username.
     * 
     * @param username the username to search for
     * @return an Optional containing the user if found, or empty if not found
     */
    Optional<User> findByUsername(String username);
    
    /**
     * Find a user by email address.
     * 
     * @param email the email address to search for
     * @return an Optional containing the user if found, or empty if not found
     */
    Optional<User> findByEmail(String email);
    
    /**
     * Find users by role name.
     * 
     * @param roleName the name of the role to search for
     * @return a list of users with the specified role
     */
    @Query("SELECT u FROM User u JOIN u.roles r WHERE r.name = :roleName")
    List<User> findByRoleName(@Param("roleName") String roleName);
    
    /**
     * Find users with Operations Staff role.
     * 
     * @return a list of users with Operations Staff role
     */
    @Query("SELECT u FROM User u JOIN u.roles r WHERE r.name = 'OPERATIONS_STAFF'")
    List<User> findOperationsStaffUsers();
    
    /**
     * Find users with System Admin role.
     * 
     * @return a list of users with System Admin role
     */
    @Query("SELECT u FROM User u JOIN u.roles r WHERE r.name = 'SYSTEM_ADMIN'")
    List<User> findSystemAdminUsers();
    
    /**
     * Check if a username already exists.
     * 
     * @param username the username to check
     * @return true if the username exists, false otherwise
     */
    boolean existsByUsername(String username);
    
    /**
     * Check if an email address already exists.
     * 
     * @param email the email address to check
     * @return true if the email exists, false otherwise
     */
    boolean existsByEmail(String email);
    
    /**
     * Find all enabled users.
     * 
     * @return a list of all enabled users
     */
    List<User> findByEnabledTrue();
    
    /**
     * Find all disabled users.
     * 
     * @return a list of all disabled users
     */
    List<User> findByEnabledFalse();
    
    /**
     * Find all locked users.
     * 
     * @return a list of all locked users
     */
    List<User> findByAccountNonLockedFalse();
    
    /**
     * Find all users with expired accounts.
     * 
     * @return a list of all users with expired accounts
     */
    List<User> findByAccountNonExpiredFalse();
    
    /**
     * Find all users with expired credentials.
     * 
     * @return a list of all users with expired credentials
     */
    List<User> findByCredentialsNonExpiredFalse();
    
    /**
     * Find users by username containing the given string (case insensitive).
     * 
     * @param username the username substring to search for
     * @return a list of users with usernames containing the given string
     */
    List<User> findByUsernameContainingIgnoreCase(String username);
    
    /**
     * Find users by email containing the given string (case insensitive).
     * 
     * @param email the email substring to search for
     * @return a list of users with emails containing the given string
     */
    List<User> findByEmailContainingIgnoreCase(String email);
    
    /**
     * Find users created after the specified timestamp.
     * 
     * @param timestamp the timestamp to compare against
     * @return a list of users created after the specified timestamp
     */
    @Query("SELECT u FROM User u WHERE u.createdAt > :timestamp")
    List<User> findByCreatedAtAfter(@Param("timestamp") java.time.LocalDateTime timestamp);
    
    /**
     * Find users updated after the specified timestamp.
     * 
     * @param timestamp the timestamp to compare against
     * @return a list of users updated after the specified timestamp
     */
    @Query("SELECT u FROM User u WHERE u.updatedAt > :timestamp")
    List<User> findByUpdatedAtAfter(@Param("timestamp") java.time.LocalDateTime timestamp);
}