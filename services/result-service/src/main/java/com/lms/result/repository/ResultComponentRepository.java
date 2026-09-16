package com.lms.result.repository;

import com.lms.result.entity.ResultComponent;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.UUID;

@Repository
public interface ResultComponentRepository extends JpaRepository<ResultComponent, UUID> {
}
