#pragma once

/*
 * Copyright (c) 2018, Yung-Yu Chen <yyc@solvcon.net>
 * BSD 3-Clause License, see COPYING
 */

/**
 * \file
 * String helpers.
 */

#include <cstdio>
#include <sstream>
#include <iostream>
#include <iomanip>
#include <string>

#include <cxxabi.h>

namespace march {

namespace string {

// FIXME: va_list format string checking
template<typename ... Args>
std::string format(const std::string & format, Args ... args) {
    size_t size = std::snprintf(nullptr, 0, format.c_str(), args ...) + 1;
    std::unique_ptr<char[]> buf(new char[size]); 
    std::snprintf(buf.get(), size, format.c_str(), args ...);
    return std::string(buf.get(), buf.get() + size - 1);
}

inline std::string create_indented_newline(size_t indent) {
    std::string indented_newline("\n");
    while (indent) { indented_newline += " "; indent--; }
    return indented_newline;
}

inline std::string replace_all_substrings(
    std::string subject, std::string const & source, std::string const & target
) {
    std::string::size_type n = 0;
    while ((n = subject.find(source, n)) != std::string::npos) {
        subject.replace(n, source.size(), target);
        n += target.size();
    }
    return subject;
}

inline std::string from_double(double value, size_t precision=0) {
    std::ostringstream os;
    os.setf(std::ios::left);
    if (precision) {
        os.setf(std::ios::scientific);
        os.precision(precision);
    }
    os << value;
    return os.str();
}

template <class T>
std::string get_type_name(const T &) {
    char * buf = abi::__cxa_demangle(typeid(T).name(), nullptr, nullptr, nullptr);
    const std::string ret(buf);
    free(buf);
    return ret;
}

} /* end namespace string */

inline std::string error_location(
    const char * filename, int lineno, const char * funcname
) {
    return string::format("in file %s, line %d, function %s", filename, lineno, funcname);
}

} /* end namespace march */

// vim: set ff=unix fenc=utf8 nobomb et sw=4 ts=4:
