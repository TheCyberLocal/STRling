/**
 * @file strling_parse_error.cpp
 * @brief Implementation of STRling error classes
 * 
 * @copyright Copyright (c) 2024 TheCyberLocal
 * @license MIT License
 */

#include "strling/core/strling_parse_error.hpp"
#include <sstream>
#include <algorithm>
#include <cctype>
#include <vector>

namespace strling {
namespace core {

STRlingParseError::STRlingParseError(
    const std::string& message,
    int pos,
    const std::string& text,
    const std::optional<std::string>& hint
)
    : message_(message)
    , pos_(pos)
    , text_(text)
    , hint_(hint)
    , formatted_(formatError())
{
}

const char* STRlingParseError::what() const noexcept {
    return formatted_.c_str();
}

std::string STRlingParseError::toFormattedString() const {
    return formatError();
}

std::string STRlingParseError::formatError() const {
    if (text_.empty()) {
        // Fallback to simple format if no text provided
        std::ostringstream oss;
        oss << message_ << " at position " << pos_;
        return oss.str();
    }
    
    // Find the line containing the error
    std::vector<std::string> lines;
    std::istringstream text_stream(text_);
    std::string line;
    while (std::getline(text_stream, line)) {
        lines.push_back(line);
    }
    
    int current_pos = 0;
    int line_num = 1;
    std::string line_text;
    int col = pos_;
    
    for (size_t i = 0; i < lines.size(); ++i) {
        int line_len = lines[i].length() + 1; // +1 for newline
        if (current_pos + line_len > pos_) {
            line_num = static_cast<int>(i + 1);
            line_text = lines[i];
            col = pos_ - current_pos;
            break;
        }
        current_pos += line_len;
    }
    
    // Error is beyond the last line
    if (line_text.empty() && !lines.empty()) {
        line_num = static_cast<int>(lines.size());
        line_text = lines.back();
        col = static_cast<int>(line_text.length());
    } else if (line_text.empty() && lines.empty()) {
        line_text = text_;
        col = pos_;
    }
    
    // Build the formatted error message
    std::ostringstream oss;
    oss << "STRling Parse Error: " << message_ << "\n";
    oss << "\n";
    oss << "> " << line_num << " | " << line_text << "\n";
    oss << ">   | " << std::string(col, ' ') << "^";
    
    if (hint_.has_value()) {
        oss << "\n";
        oss << "\n";
        oss << "Hint: " << hint_.value();
    }
    
    return oss.str();
}

std::map<std::string, std::string> STRlingParseError::toLspDiagnostic() const {
    // Find the line and column containing the error
    std::vector<std::string> lines;
    if (!text_.empty()) {
        std::istringstream text_stream(text_);
        std::string line;
        while (std::getline(text_stream, line)) {
            lines.push_back(line);
        }
    }
    
    int current_pos = 0;
    int line_num = 0; // 0-indexed for LSP
    int col = pos_;
    
    for (size_t i = 0; i < lines.size(); ++i) {
        int line_len = lines[i].length() + 1; // +1 for newline
        if (current_pos + line_len > pos_) {
            line_num = static_cast<int>(i);
            col = pos_ - current_pos;
            break;
        }
        current_pos += line_len;
    }
    
    // Error is beyond the last line
    if (!lines.empty() && line_num == 0 && current_pos > 0) {
        line_num = static_cast<int>(lines.size() - 1);
        col = static_cast<int>(lines.back().length());
    }
    
    // Build the diagnostic message
    std::string diagnostic_message = message_;
    if (hint_.has_value()) {
        diagnostic_message += "\n\nHint: " + hint_.value();
    }
    
    // Create error code from message (normalize to snake_case)
    std::string error_code = message_;
    std::transform(error_code.begin(), error_code.end(), error_code.begin(),
                   [](unsigned char c) { return std::tolower(c); });
    
    // Replace special characters with underscores
    const std::string special_chars = " '\"()[]{}\\/ ";
    for (char& c : error_code) {
        if (special_chars.find(c) != std::string::npos) {
            c = '_';
        }
    }
    
    // Remove consecutive underscores
    auto new_end = std::unique(error_code.begin(), error_code.end(),
                              [](char a, char b) { return a == '_' && b == '_'; });
    error_code.erase(new_end, error_code.end());
    
    // Trim leading/trailing underscores
    error_code.erase(0, error_code.find_first_not_of('_'));
    error_code.erase(error_code.find_last_not_of('_') + 1);
    
    // Note: This is a simplified version that returns string-to-string map
    // A full implementation would need a more complex data structure or JSON library
    std::map<std::string, std::string> diagnostic;
    diagnostic["severity"] = "1"; // 1 = Error
    diagnostic["message"] = diagnostic_message;
    diagnostic["source"] = "STRling";
    diagnostic["code"] = error_code;
    diagnostic["line_start"] = std::to_string(line_num);
    diagnostic["col_start"] = std::to_string(col);
    diagnostic["line_end"] = std::to_string(line_num);
    diagnostic["col_end"] = std::to_string(col + 1);
    
    return diagnostic;
}

} // namespace core
} // namespace strling
